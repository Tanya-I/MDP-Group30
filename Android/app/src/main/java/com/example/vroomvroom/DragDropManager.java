// DragDropManager.java
package com.example.vroomvroom;

import android.graphics.Rect;
import android.os.Handler;
import android.view.MotionEvent;
import android.view.View;

public class DragDropManager {
    private float dX, dY;
    private boolean isDragging = false;
    private OnDragEventListener eventListener;
    private CustomGridView targetGrid;

    // Click detection variables
    private static final long CLICK_TIME_THRESHOLD = 200; // in ms max time for a click
    private static final float CLICK_DISTANCE_THRESHOLD = 10; // in pixels max movement for a click
    private static final long DOUBLE_CLICK_TIME_DELTA = 300; // in ms time between clicks for double-click

    private long touchDownTime = 0;
    private float touchDownX = 0;
    private float touchDownY = 0;
    private boolean isClick = false;
    private Handler clickHandler = new Handler();

    public interface OnDragEventListener {
        void onDragMessage(String message);
        void onItemDropped(String itemName, float x, float y);
        void onGridItemDropped(String itemName, int gridX, int gridY);

        // Add click event methods
        void onItemSingleClick(String itemName);
        void onItemDoubleClick(String itemName);
    }

    public DragDropManager() {}

    public void setEventListener(OnDragEventListener listener) {
        this.eventListener = listener;
    }

    public void setTargetGrid(CustomGridView grid) {
        this.targetGrid = grid;
    }

    public View.OnTouchListener createDragTouchListener(String itemName) {
        return new View.OnTouchListener() {
            private long lastClickTime = 0;
            private Runnable singleClickRunnable;

            @Override
            public boolean onTouch(View view, MotionEvent event) {
                return handleTouchEvent(view, event, itemName);
            }

            private boolean handleTouchEvent(View view, MotionEvent event, String itemName) {
                switch (event.getAction()) {
                    case MotionEvent.ACTION_DOWN:
                        // Record touch start
                        touchDownTime = System.currentTimeMillis();
                        touchDownX = event.getRawX();
                        touchDownY = event.getRawY();

                        // Initialize drag variables
                        dX = view.getX() - event.getRawX();
                        dY = view.getY() - event.getRawY();
                        isDragging = false;
                        isClick = true;

                        notifyMessage("DEBUG: " + itemName + " touch down at " + touchDownTime);
                        return true;

                    case MotionEvent.ACTION_MOVE:
                        float deltaX = Math.abs(event.getRawX() - touchDownX);
                        float deltaY = Math.abs(event.getRawY() - touchDownY);

                        // Check if movement exceeds click threshold
                        if (deltaX > CLICK_DISTANCE_THRESHOLD || deltaY > CLICK_DISTANCE_THRESHOLD) {
                            if (isClick) {
                                isClick = false;
                                notifyMessage("DEBUG: " + itemName + " movement detected - switching to drag mode");
                            }

                            if (!isDragging) {
                                isDragging = true;
                                notifyMessage("Dragging " + itemName + "...");
                            }

                            float newX = event.getRawX() + dX;
                            float newY = event.getRawY() + dY;

                            // Basic boundary checking
                            View parent = (View) view.getParent();
                            if (parent != null) {
                                if (newX >= 0 && newX <= (parent.getWidth() - view.getWidth())) {
                                    view.setX(newX);
                                }
                                if (newY >= 0 && newY <= (parent.getHeight() - view.getHeight())) {
                                    view.setY(newY);
                                }
                            }
                        }
                        return true;

                    case MotionEvent.ACTION_UP:
                        long touchDuration = System.currentTimeMillis() - touchDownTime;

                        if (isDragging) {
                            // Handle drag completion
                            float finalX = Math.round(view.getX());
                            float finalY = Math.round(view.getY());

                            // Check if dropped on grid
                            if (targetGrid != null) {
                                int[] gridCoords = getExactGridCoordinates(event.getRawX(), event.getRawY());
                                if (gridCoords != null) {
                                    // Successfully dropped on grid
                                    notifyMessage(itemName + " placed on grid at (" + gridCoords[0] + ", " + gridCoords[1] + ")");

                                    if (eventListener != null) {
                                        eventListener.onGridItemDropped(itemName, gridCoords[0], gridCoords[1]);
                                    }
                                    isDragging = false;
                                    return true;
                                }
                            }

                            // If not dropped on grid, trigger the outside grid handler
                            notifyMessage(itemName + " dropped outside grid area");

                            if (eventListener != null) {
                                eventListener.onItemDropped(itemName, finalX, finalY);
                            }
                            isDragging = false;

                        } else if (isClick && touchDuration < CLICK_TIME_THRESHOLD) {
                            // Handle click detection
                            long currentTime = System.currentTimeMillis();
                            notifyMessage("DEBUG: " + itemName + " click detected at " + currentTime);

                            if (currentTime - lastClickTime < DOUBLE_CLICK_TIME_DELTA) {
                                // Double click detected
                                notifyMessage("DEBUG: Double-click detected on " + itemName);

                                // Cancel any pending single click
                                if (singleClickRunnable != null) {
                                    clickHandler.removeCallbacks(singleClickRunnable);
                                    notifyMessage("DEBUG: Cancelled pending single-click for " + itemName);
                                }

                                // Execute double click
                                if (eventListener != null) {
                                    eventListener.onItemDoubleClick(itemName);
                                }

                            } else {
                                // Potential single click - wait to see if double click follows
                                notifyMessage("DEBUG: Potential single-click on " + itemName + ", waiting...");

                                singleClickRunnable = new Runnable() {
                                    @Override
                                    public void run() {
                                        notifyMessage("DEBUG: Executing single-click for " + itemName);
                                        if (eventListener != null) {
                                            eventListener.onItemSingleClick(itemName);
                                        }
                                    }
                                };

                                clickHandler.postDelayed(singleClickRunnable, DOUBLE_CLICK_TIME_DELTA);
                            }

                            lastClickTime = currentTime;
                        }

                        // Reset state
                        isDragging = false;
                        isClick = false;
                        return true;

                    default:
                        return false;
                }
            }
        };
    }

    private int[] getExactGridCoordinates(float screenX, float screenY) {
        if (targetGrid == null) return null;

        // Get grid bounds
        Rect gridBounds = new Rect();
        targetGrid.getGlobalVisibleRect(gridBounds);

        // Check if the drop position is within the actual grid area
        if (screenX >= gridBounds.left && screenX <= gridBounds.right &&
                screenY >= gridBounds.top && screenY <= gridBounds.bottom) {

            // Use the CustomGridView's method to get coordinates
            int[] coords = targetGrid.getGridCoordinatesFromScreenPosition(screenX, screenY);

            // Only return coordinates if they are valid (within the 20x20 grid)
            if (coords != null && coords[0] >= 0 && coords[0] < 20 && coords[1] >= 0 && coords[1] < 20) {
                return coords;
            }
        }

        return null; // Outside grid or invalid coordinates
    }

    // NOT IN USE CODE METHOD (CLEAN UP LATER)
//    private int[] getNearestGridCell(float screenX, float screenY) {
//        if (targetGrid == null) return null;
//
//        // First try to get exact coordinates using CustomGridView's method
//        int[] exactCoords = targetGrid.getGridCoordinatesFromScreenPosition(screenX, screenY);
//        if (exactCoords != null) {
//            return exactCoords; // Direct hit on a valid grid cell
//        }
//
//        // If not a direct hit, calculate the nearest cell by extending the grid logic
//        // Get this view's position on screen (matching CustomGridView's approach)
//        int[] viewLocation = new int[2];
//        targetGrid.getLocationOnScreen(viewLocation);
//
//        // Convert screen coordinates to view-relative coordinates
//        float viewRelativeX = screenX - viewLocation[0];
//        float viewRelativeY = screenY - viewLocation[1];
//
//        // Use the same grid calculation as CustomGridView but without bounds checking
//        // We need to replicate the CustomGridView's internal calculation
//        Rect gridBounds = new Rect();
//        targetGrid.getGlobalVisibleRect(gridBounds);
//
//        float viewWidth = gridBounds.width();
//        float viewHeight = gridBounds.height();
//
//        // Match CustomGridView's cell calculation
//        float cellWidth = viewWidth / 21.0f;  // 21 columns total
//        float cellHeight = viewHeight / 21.0f; // 21 rows total
//
//        // Match CustomGridView's grid start position
//        float gridStartX = cellWidth;  // Skip Y-label column
//        float gridStartY = 0;          // No Y offset
//
//        // Adjust for the grid offset (same as CustomGridView)
//        float adjustedX = viewRelativeX - gridStartX;
//        float adjustedY = viewRelativeY - gridStartY;
//
//        // Calculate grid cell position (allowing out-of-bounds for clamping)
//        float exactX = adjustedX / cellWidth;
//        float exactY = adjustedY / cellHeight;
//
//        // Round to nearest cell and clamp to valid grid bounds (0-19)
//        int gridSize = 20;
//        int visualX = Math.max(0, Math.min(gridSize - 1, Math.round(exactX)));
//        int visualY = Math.max(0, Math.min(gridSize - 1, Math.round(exactY)));
//
//        // Convert visual coordinates to logical coordinates (flip Y axis, same as CustomGridView)
//        int logicalX = visualX;
//        int logicalY = gridSize - 1 - visualY;
//
//        return new int[]{logicalX, logicalY};
//    }

    private void notifyMessage(String message) {
        if (eventListener != null) {
            eventListener.onDragMessage(message);
        }
    }
}

