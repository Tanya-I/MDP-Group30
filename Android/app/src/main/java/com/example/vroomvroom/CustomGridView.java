// CustomGridView.java
package com.example.vroomvroom;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.util.AttributeSet;
import android.view.View;
import android.view.ViewTreeObserver;
import java.util.HashSet;
import java.util.Set;

public class CustomGridView extends View {
    private Paint gridPaint;
    private Paint robotPaint;
    private Paint pathPaint;
    private int gridSize = 20;
    private float cellWidth;
    private float cellHeight;
    private float gridStartX;
    private float gridStartY;

    private int robotX = -1;
    private int robotY = -1;

    // Path tracking
    private Set<String> visitedCells = new HashSet<>();

    private View tableLayoutReference;
    private boolean isInitialized = false;

    public CustomGridView(Context context) {
        super(context);
        init();
    }

    public CustomGridView(Context context, AttributeSet attrs) {
        super(context, attrs);
        init();
    }

    private void init() {
        gridPaint = new Paint();
        gridPaint.setColor(0xFF999999);
        gridPaint.setStrokeWidth(1.0f);
        gridPaint.setStyle(Paint.Style.STROKE);
        gridPaint.setAntiAlias(true);

        robotPaint = new Paint();
        robotPaint.setColor(0xFF0000FF);
        robotPaint.setStyle(Paint.Style.FILL);
        robotPaint.setAntiAlias(true);

        pathPaint = new Paint();
        pathPaint.setColor(0x80ADD8E6);
        pathPaint.setStyle(Paint.Style.FILL);
        pathPaint.setAntiAlias(true);
    }

    public void setTableLayoutReference(View tableLayout) {
        this.tableLayoutReference = tableLayout;

        if (tableLayout != null) {
            tableLayout.getViewTreeObserver().addOnGlobalLayoutListener(new ViewTreeObserver.OnGlobalLayoutListener() {
                @Override
                public void onGlobalLayout() {
                    calculateDimensionsFromTableLayout();
                    tableLayout.getViewTreeObserver().removeOnGlobalLayoutListener(this);
                }
            });
        }
    }

    private void calculateDimensionsFromTableLayout() {
        if (tableLayoutReference == null) return;

        int tableWidth = tableLayoutReference.getWidth();
        int tableHeight = tableLayoutReference.getHeight();

        if (tableWidth > 0 && tableHeight > 0) {
            // Calculate cell dimensions based on TableLayout
            // TableLayout has 21 columns and 21 rows total (label row also counted )
            cellWidth = tableWidth / 21.0f;
            cellHeight = tableHeight / 21.0f;

            // Grid starts after the Y-label column
            gridStartX = cellWidth;
            // Grid starts at the top
            gridStartY = 0;

            isInitialized = true;
            invalidate();
        }
    }

    @Override
    protected void onSizeChanged(int w, int h, int oldw, int oldh) {
        super.onSizeChanged(w, h, oldw, oldh);

        // Fallback calculation if TableLayout reference isn't available
        if (!isInitialized && tableLayoutReference == null) {
            cellWidth = w / 21.0f;
            cellHeight = h / 21.0f;
            gridStartX = cellWidth;
            gridStartY = 0;
            isInitialized = true;
        }
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);

        if (!isInitialized || cellWidth <= 0 || cellHeight <= 0) return;

        // Draw the visited path cells first (so they appear behind grid lines)
        drawVisitedCells(canvas);

        // Draw the grid lines over the data area only (20x20 grid, excluding labels)
        float gridWidth = gridSize * cellWidth;
        float gridHeight = gridSize * cellHeight;

        // Draw vertical grid lines
        for (int i = 0; i <= gridSize; i++) {
            float x = gridStartX + (i * cellWidth);
            canvas.drawLine(x, gridStartY, x, gridStartY + gridHeight, gridPaint);
        }

        // Draw horizontal grid lines
        for (int i = 0; i <= gridSize; i++) {
            float y = gridStartY + (i * cellHeight);
            canvas.drawLine(gridStartX, y, gridStartX + gridWidth, y, gridPaint);
        }
    }

    private void drawVisitedCells(Canvas canvas) {
        for (String cellKey : visitedCells) {
            String[] coords = cellKey.split(",");
            int x = Integer.parseInt(coords[0]);
            int y = Integer.parseInt(coords[1]);

            float[] cellPos = getCellPosition(x, y);
            if (cellPos != null) {
                canvas.drawRect(cellPos[0], cellPos[1],
                        cellPos[0] + cellPos[2], cellPos[1] + cellPos[3],
                        pathPaint);
            }
        }
    }

    public void setRobotPosition(int x, int y) {
        this.robotX = x;
        this.robotY = y;

        // Add 2x2 area to visited cells if it's a valid grid position
        // Robot coordinate (x,y) represents the bottom-left corner of the 2x2 area
        if (x >= 0 && y >= 0 && x < gridSize - 1 && y < gridSize - 1) {
            // Add all four cells of the 2x2 area
            visitedCells.add(x + "," + y);           // bottom-left
            visitedCells.add((x + 1) + "," + y);     // bottom-right
            visitedCells.add(x + "," + (y + 1));     // top-left
            visitedCells.add((x + 1) + "," + (y + 1)); // top-right
        } else if (x >= 0 && y >= 0 && x < gridSize && y < gridSize) {
            // Handle edge cases where robot is at boundary
            // Add cells that are within bounds
            if (x < gridSize && y < gridSize) {
                visitedCells.add(x + "," + y);
            }
            if (x + 1 < gridSize && y < gridSize) {
                visitedCells.add((x + 1) + "," + y);
            }
            if (x < gridSize && y + 1 < gridSize) {
                visitedCells.add(x + "," + (y + 1));
            }
            if (x + 1 < gridSize && y + 1 < gridSize) {
                visitedCells.add((x + 1) + "," + (y + 1));
            }
        }

        invalidate();
    }

    public void clearPath() {
        visitedCells.clear();
        invalidate();
    }

    public void setPathColor(int color) {
        pathPaint.setColor(color);
        invalidate();
    }

    public int getVisitedCellCount() {
        // Return the count of 2x2 areas visited, not individual cells
        // This is a bit complex since we store individual cells but want to count 2x2 areas
        Set<String> visitedAreas = new HashSet<>();

        for (String cellKey : visitedCells) {
            String[] coords = cellKey.split(",");
            int x = Integer.parseInt(coords[0]);
            int y = Integer.parseInt(coords[1]);

            // For each cell, determine if it could be the bottom-left of a 2x2 area
            // Check if all 4 cells of the potential 2x2 area are visited
            if (visitedCells.contains(x + "," + y) &&
                    visitedCells.contains((x + 1) + "," + y) &&
                    visitedCells.contains(x + "," + (y + 1)) &&
                    visitedCells.contains((x + 1) + "," + (y + 1))) {
                visitedAreas.add(x + "," + y); // Use bottom-left as the area identifier
            }
        }

        return visitedAreas.size();
    }

    public Set<String> getVisitedCells() {
        return new HashSet<>(visitedCells);
    }

    public int[] getGridCoordinatesFromScreenPosition(float screenX, float screenY) {
        if (!isInitialized) return null;

        // Get this view's position on screen
        int[] viewLocation = new int[2];
        getLocationOnScreen(viewLocation);

        // Convert screen coordinates to view-relative coordinates
        float viewRelativeX = screenX - viewLocation[0];
        float viewRelativeY = screenY - viewLocation[1];

        // Adjust for the grid offset (skip Y-label column)
        float adjustedX = viewRelativeX - gridStartX;
        float adjustedY = viewRelativeY - gridStartY;

        // Calculate grid cell position
        int visualX = (int) (adjustedX / cellWidth);
        int visualY = (int) (adjustedY / cellHeight);

        // Check if within valid grid bounds
        if (visualX >= 0 && visualX < gridSize && visualY >= 0 && visualY < gridSize) {
            // Convert visual coordinates to logical coordinates (flip Y axis)
            int logicalX = visualX;
            int logicalY = gridSize - 1 - visualY;

            return new int[]{logicalX, logicalY};
        }

        return null; // Outside grid bounds
    }

    public float[] getCellPosition(int logicalX, int logicalY) {
        if (!isInitialized) return null;

        if (logicalX < 0 || logicalX >= gridSize || logicalY < 0 || logicalY >= gridSize) {
            return null;
        }

        // Convert logical coordinates to visual coordinates
        int visualX = logicalX;
        int visualY = gridSize - 1 - logicalY; // Flip Y axis

        // Calculate position (accounting for grid start offset)
        float x = gridStartX + (visualX * cellWidth);
        float y = gridStartY + (visualY * cellHeight);

        return new float[]{x, y, cellWidth, cellHeight};
    }

    public float[] getCellCenterPosition(int gridX, int gridY) {
        if (!isInitialized) return null;

        // Convert logical coordinates to visual coordinates
        int visualX = gridX;
        int visualY = gridSize - 1 - gridY; // Flip Y axis

        // Calculate center position
        float centerX = gridStartX + (visualX + 0.5f) * cellWidth;
        float centerY = gridStartY + (visualY + 0.5f) * cellHeight;

        return new float[]{centerX, centerY};
    }

    // New method to get the 2x2 area position for the robot
    public float[] getRobot2x2Position(int robotX, int robotY) {
        if (!isInitialized) return null;

        if (robotX < 0 || robotX >= gridSize || robotY < 0 || robotY >= gridSize) {
            return null;
        }

        // Convert logical coordinates to visual coordinates
        int visualX = robotX;
        int visualY = gridSize - 1 - robotY; // Flip Y axis

        // Calculate position for 2x2 area (bottom-left corner of robot)
        float x = gridStartX + (visualX * cellWidth);
        float y = gridStartY + ((visualY - 1) * cellHeight); // -1 because robot extends upward

        // Return position and dimensions for 2x2 area
        return new float[]{x, y, cellWidth * 2, cellHeight * 2};
    }
}