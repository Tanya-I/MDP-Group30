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

                            View parent = (View) view.getParent();
                            if (parent != null) {
                                if (newX >= 0 && newX <= (parent.getWidth() - view.getWidth())) {
                                    view.setX(newX);
                                }
                                if (newY >= 0 && newY <= (parent.getHeight() - view.getHeight())) {
                                    view.setY(newY);
                                }
                            }

                            updateHoverHighlight(event.getRawX(), event.getRawY());
                        }
                        return true;

                    case MotionEvent.ACTION_UP:
                        if (targetGrid != null) {
                            targetGrid.clearHover();
                        }

                        long touchDuration = System.currentTimeMillis() - touchDownTime;

                        if (isDragging) {

                            float finalX = Math.round(view.getX());
                            float finalY = Math.round(view.getY());


                            if (targetGrid != null) {
                                int[] gridCoords = getExactGridCoordinates(event.getRawX(), event.getRawY());
                                if (gridCoords != null) {

                                    notifyMessage(itemName + " placed on grid at (" + gridCoords[0] + ", " + gridCoords[1] + ")");

                                    if (eventListener != null) {
                                        eventListener.onGridItemDropped(itemName, gridCoords[0], gridCoords[1]);
                                    }
                                    isDragging = false;
                                    return true;
                                }
                            }

                            notifyMessage(itemName + " dropped outside grid area");

                            if (eventListener != null) {
                                eventListener.onItemDropped(itemName, finalX, finalY);
                            }
                            isDragging = false;

                        } else if (isClick && touchDuration < CLICK_TIME_THRESHOLD) {

                            long currentTime = System.currentTimeMillis();
                            notifyMessage("DEBUG: " + itemName + " click detected at " + currentTime);

                            if (currentTime - lastClickTime < DOUBLE_CLICK_TIME_DELTA) {

                                notifyMessage("DEBUG: Double-click detected on " + itemName);

                                if (singleClickRunnable != null) {
                                    clickHandler.removeCallbacks(singleClickRunnable);
                                    notifyMessage("DEBUG: Cancelled pending single-click for " + itemName);
                                }

                                // Execute double click
                                if (eventListener != null) {
                                    eventListener.onItemDoubleClick(itemName);
                                }

                            } else {
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

                    case MotionEvent.ACTION_CANCEL:
                        if (targetGrid != null) {
                            targetGrid.clearHover();
                        }
                        isDragging = false;
                        isClick = false;
                        return true;

                    default:
                        return false;
                }
            }
        };
    }

    private void updateHoverHighlight(float screenX, float screenY) {
        if (targetGrid == null) return;

        int[] gridCoords = getExactGridCoordinates(screenX, screenY);

        if (gridCoords != null) {
            targetGrid.setHoverPosition(gridCoords[0], gridCoords[1]);
        } else {
            targetGrid.clearHover();
        }
    }

    private int[] getExactGridCoordinates(float screenX, float screenY) {
        if (targetGrid == null) return null;

        Rect gridBounds = new Rect();
        targetGrid.getGlobalVisibleRect(gridBounds);

        if (screenX >= gridBounds.left && screenX <= gridBounds.right &&
                screenY >= gridBounds.top && screenY <= gridBounds.bottom) {

            int[] coords = targetGrid.getGridCoordinatesFromScreenPosition(screenX, screenY);

            if (coords != null && coords[0] >= 0 && coords[0] < 20 && coords[1] >= 0 && coords[1] < 20) {
                return coords;
            }
        }

        return null; // Outside grid or invalid coordinates
    }


    private void notifyMessage(String message) {
        if (eventListener != null) {
            eventListener.onDragMessage(message);
        }
    }
}