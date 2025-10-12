// RobotManager.java
package com.example.vroomvroom;

public class RobotManager {

    public interface RobotUpdateListener {
        void onRobotPositionChanged(int x, int y, String direction);
        void onRobotPositionChangedNoSend(int x, int y, String direction); // New method for Bluetooth updates
        void onRobotMoved(int oldX, int oldY, int newX, int newY, String direction);
        void onStatusMessage(String message);
    }

    private RobotUpdateListener listener;

    // Robot state
    private int robotX = -1;
    private int robotY = -1;
    private String robotDirection = "N";

    // Grid boundaries
    private final int MIN_X = 0;
    private final int MAX_X = 19;
    private final int MIN_Y = 0;
    private final int MAX_Y = 19;

    // Robot size - 2x2 robot with coordinate at bottom-left
    private final int ROBOT_SIZE = 2;

    public void setListener(RobotUpdateListener listener) {
        this.listener = listener;
    }

    // Position Management (sends Bluetooth - for drag/drop operations)
    public void setRobotPosition(int x, int y) {
        if (x == -1 && y == -1) {
            // Handle off-grid position - robot is not on the grid
            int oldX = robotX;
            int oldY = robotY;
            robotX = x;
            robotY = y;

            if (listener != null) {
                listener.onRobotPositionChanged(robotX, robotY, robotDirection);
                if (oldX != robotX || oldY != robotY) {
                    listener.onRobotMoved(oldX, oldY, robotX, robotY, robotDirection);
                }
                listener.onStatusMessage("Robot position set to off-grid");
            }
            return;
        }

        if (isValidPosition(x, y)) {
            int oldX = robotX;
            int oldY = robotY;
            robotX = x;
            robotY = y;

            if (listener != null) {
                listener.onRobotPositionChanged(robotX, robotY, robotDirection);
                if (oldX != x || oldY != y) {
                    listener.onRobotMoved(oldX, oldY, robotX, robotY, robotDirection);
                }
            }
        } else {
            if (listener != null) {
                listener.onStatusMessage("Invalid robot position: (" + x + ", " + y + ") - 2x2 robot doesn't fit");
            }
        }
    }

    // NEW: Position management without sending Bluetooth (for movement commands)
    private void setRobotPositionNoSend(int x, int y) {
        if (x == -1 && y == -1) {
            // Handle off-grid position - robot is not on the grid
            int oldX = robotX;
            int oldY = robotY;
            robotX = x;
            robotY = y;

            if (listener != null) {
                listener.onRobotPositionChangedNoSend(robotX, robotY, robotDirection);
                if (oldX != robotX || oldY != robotY) {
                    listener.onRobotMoved(oldX, oldY, robotX, robotY, robotDirection);
                }
                listener.onStatusMessage("Robot position set to off-grid");
            }
            return;
        }

        if (isValidPosition(x, y)) {
            int oldX = robotX;
            int oldY = robotY;
            robotX = x;
            robotY = y;

            if (listener != null) {
                listener.onRobotPositionChangedNoSend(robotX, robotY, robotDirection);
                if (oldX != x || oldY != y) {
                    listener.onRobotMoved(oldX, oldY, robotX, robotY, robotDirection);
                }
            }
        } else {
            if (listener != null) {
                listener.onStatusMessage("Invalid robot position: (" + x + ", " + y + ") - 2x2 robot doesn't fit");
            }
        }
    }

    public void setRobotDirection(String direction) {
        if (isValidDirection(direction)) {
            String oldDirection = robotDirection;
            robotDirection = direction;

            if (listener != null) {
                listener.onRobotPositionChanged(robotX, robotY, robotDirection);
                listener.onStatusMessage("Robot direction changed from " + oldDirection + " to " + direction);
            }
        } else {
            if (listener != null) {
                listener.onStatusMessage("Invalid robot direction: " + direction);
            }
        }
    }

    // NEW: Direction change without sending Bluetooth (for movement commands)
    private void setRobotDirectionNoSend(String direction) {
        if (isValidDirection(direction)) {
            String oldDirection = robotDirection;
            robotDirection = direction;

            if (listener != null) {
                listener.onRobotPositionChangedNoSend(robotX, robotY, robotDirection);
                listener.onStatusMessage("Robot direction changed from " + oldDirection + " to " + direction);
            }
        } else {
            if (listener != null) {
                listener.onStatusMessage("Invalid robot direction: " + direction);
            }
        }
    }

    // Method for Bluetooth updates that shouldn't be sent back
    public void setRobotPositionFromBluetooth(int x, int y, String direction) {
        boolean positionChanged = false;
        boolean directionChanged = false;

        // Handle reset/unknown position
        if (x == -1 && y == -1) {
            int oldX = robotX;
            int oldY = robotY;
            robotX = 1;
            robotY = 1;
            positionChanged = (oldX != robotX || oldY != robotY);

            if (listener != null && positionChanged) {
                listener.onRobotMoved(oldX, oldY, robotX, robotY, robotDirection);
                listener.onStatusMessage("Robot position reset to default (1, 1)");
            }
        } else if (isValidPosition(x, y)) {
            int oldX = robotX;
            int oldY = robotY;
            robotX = x;
            robotY = y;
            positionChanged = (oldX != x || oldY != y);

            if (listener != null && positionChanged) {
                listener.onRobotMoved(oldX, oldY, robotX, robotY, robotDirection);
            }
        } else {
            if (listener != null) {
                listener.onStatusMessage("Invalid robot position: (" + x + ", " + y + ") - 2x2 robot doesn't fit");
            }
            return; // Don't update direction if position is invalid
        }

        // Update direction if valid
        if (isValidDirection(direction)) {
            String oldDirection = robotDirection;
            robotDirection = direction;
            directionChanged = !oldDirection.equals(direction);

            if (listener != null && directionChanged) {
                listener.onStatusMessage("Robot direction changed from " + oldDirection + " to " + direction);
            }
        } else {
            if (listener != null) {
                listener.onStatusMessage("Invalid robot direction: " + direction);
            }
        }

        // Use the NoSend version to prevent Bluetooth feedback loop
        if ((positionChanged || directionChanged) && listener != null) {
            listener.onRobotPositionChangedNoSend(robotX, robotY, robotDirection);
        }
    }

    // New method to set both position and direction at once (for user interactions)
    public void setRobotPositionAndDirection(int x, int y, String direction) {
        boolean positionChanged = false;
        boolean directionChanged = false;

        // Handle reset/unknown position
        if (x == -1 && y == -1) {
            int oldX = robotX;
            int oldY = robotY;
            robotX = 1;
            robotY = 1;
            positionChanged = (oldX != robotX || oldY != robotY);

            if (listener != null && positionChanged) {
                listener.onRobotMoved(oldX, oldY, robotX, robotY, robotDirection);
                listener.onStatusMessage("Robot position reset to default (1, 1)");
            }
        } else if (isValidPosition(x, y)) {
            int oldX = robotX;
            int oldY = robotY;
            robotX = x;
            robotY = y;
            positionChanged = (oldX != x || oldY != y);

            if (listener != null && positionChanged) {
                listener.onRobotMoved(oldX, oldY, robotX, robotY, robotDirection);
            }
        } else {
            if (listener != null) {
                listener.onStatusMessage("Invalid robot position: (" + x + ", " + y + ") - 2x2 robot doesn't fit");
            }
            return; // Don't update direction if position is invalid
        }

        // Update direction if valid
        if (isValidDirection(direction)) {
            String oldDirection = robotDirection;
            robotDirection = direction;
            directionChanged = !oldDirection.equals(direction);

            if (listener != null && directionChanged) {
                listener.onStatusMessage("Robot direction changed from " + oldDirection + " to " + direction);
            }
        } else {
            if (listener != null) {
                listener.onStatusMessage("Invalid robot direction: " + direction);
            }
        }

        // Notify position change if either position or direction changed
        if ((positionChanged || directionChanged) && listener != null) {
            listener.onRobotPositionChanged(robotX, robotY, robotDirection);
        }
    }

    // Movement - moves forward in current direction (NO BLUETOOTH SENDING)
    public boolean moveRobot() {
        int newX = robotX;
        int newY = robotY;

        switch (robotDirection) {
            case "N":
                newY = Math.min(robotY + 1, MAX_Y - ROBOT_SIZE + 1);
                break;
            case "S":
                newY = Math.max(robotY - 1, MIN_Y);
                break;
            case "E":
                newX = Math.min(robotX + 1, MAX_X - ROBOT_SIZE + 1);
                break;
            case "W":
                newX = Math.max(robotX - 1, MIN_X);
                break;
        }

        if (newX != robotX || newY != robotY) {
            setRobotPositionNoSend(newX, newY); // Use NoSend version
            return true;
        } else {
            if (listener != null) {
                listener.onStatusMessage("Robot cannot move " + robotDirection + " - at boundary");
            }
            return false;
        }
    }

    // Updated method for relative directional movement (NO BLUETOOTH SENDING)
    public boolean moveRobotInDirection(String relativeDirection) {
        switch (relativeDirection) {
            case "FORWARD":
            case "N": // North relative to robot (forward)
                return moveRobot(); // Move forward in current direction
            case "BACKWARD":
            case "S": // South relative to robot (backward)
                return moveBackward();
            case "LEFT":
            case "W": // West relative to robot (left turn)
                return turnLeft();
            case "RIGHT":
            case "E": // East relative to robot (right turn)
                return turnRight();
            default:
                if (listener != null) {
                    listener.onStatusMessage("Invalid relative direction: " + relativeDirection);
                }
                return false;
        }
    }

    // Method for absolute directional movement (if still needed)
    public boolean moveRobotToAbsoluteDirection(String absoluteDirection) {
        // If robot is already facing the direction, just move forward
        if (robotDirection.equals(absoluteDirection)) {
            return moveRobot();
        }

        // Robot needs to turn to face the direction
        // Determine if it's a left or right turn
        String turnType = getTurnType(robotDirection, absoluteDirection);

        if (turnType.equals("left")) {
            return turnLeft();
        } else if (turnType.equals("right")) {
            return turnRight();
        } else {
            // 180-degree turn - do two 90-degree turns
            if (turnLeft()) {
                return turnLeft(); // Turn left twice for 180 degrees
            }
            return false;
        }
    }

    // New method for moving backward (NO BLUETOOTH SENDING)
    public boolean moveBackward() {
        int newX = robotX;
        int newY = robotY;

        // Move in opposite direction to current facing
        switch (robotDirection) {
            case "N":
                newY = Math.max(robotY - 1, MIN_Y); // Move south when facing north
                break;
            case "S":
                newY = Math.min(robotY + 1, MAX_Y - ROBOT_SIZE + 1); // Move north when facing south
                break;
            case "E":
                newX = Math.max(robotX - 1, MIN_X); // Move west when facing east
                break;
            case "W":
                newX = Math.min(robotX + 1, MAX_X - ROBOT_SIZE + 1); // Move east when facing west
                break;
        }

        if (newX != robotX || newY != robotY) {
            setRobotPositionNoSend(newX, newY); // Use NoSend version
            return true;
        } else {
            if (listener != null) {
                listener.onStatusMessage("Robot cannot move backward - at boundary");
            }
            return false;
        }
    }

    // New turning methods with arc movement (NO BLUETOOTH SENDING)
    public boolean turnLeft() {
        String newDirection = getLeftDirection(robotDirection);
        return performTurn(newDirection, "left");
    }

    public boolean turnRight() {
        String newDirection = getRightDirection(robotDirection);
        return performTurn(newDirection, "right");
    }

    private boolean performTurn(String newDirection, String turnType) {
        // Calculate arc movement based on current direction and turn type
        int newX = robotX;
        int newY = robotY;

        // Corrected arc movement logic - smaller movements for more precise control, accounting for 2x2 robot size
        switch (robotDirection) {
            case "N": // Facing North
                if (turnType.equals("right")) {
                    // Turning right from North to East: move right and forward slightly
                    newX = Math.min(robotX + 1, MAX_X - ROBOT_SIZE + 1);
                    newY = Math.min(robotY + 1, MAX_Y - ROBOT_SIZE + 1);
                } else {
                    // Turning left from North to West: move left and forward slightly
                    newX = Math.max(robotX - 1, MIN_X);
                    newY = Math.min(robotY + 1, MAX_Y - ROBOT_SIZE + 1);
                }
                break;
            case "E": // Facing East
                if (turnType.equals("right")) {
                    // Turning right from East to South: move forward and down slightly
                    newX = Math.min(robotX + 1, MAX_X - ROBOT_SIZE + 1);
                    newY = Math.max(robotY - 1, MIN_Y);
                } else {
                    // Turning left from East to North: move forward and up slightly
                    newX = Math.min(robotX + 1, MAX_X - ROBOT_SIZE + 1);
                    newY = Math.min(robotY + 1, MAX_Y - ROBOT_SIZE + 1);
                }
                break;
            case "S": // Facing South
                if (turnType.equals("right")) {
                    // Turning right from South to West: move left and backward slightly
                    newX = Math.max(robotX - 1, MIN_X);
                    newY = Math.max(robotY - 1, MIN_Y);
                } else {
                    // Turning left from South to East: move right and backward slightly
                    newX = Math.min(robotX + 1, MAX_X - ROBOT_SIZE + 1);
                    newY = Math.max(robotY - 1, MIN_Y);
                }
                break;
            case "W": // Facing West
                if (turnType.equals("right")) {
                    // Turning right from West to North: move backward and up slightly
                    newX = Math.max(robotX - 1, MIN_X);
                    newY = Math.min(robotY + 1, MAX_Y - ROBOT_SIZE + 1);
                } else {
                    // Turning left from West to South: move backward and down slightly
                    newX = Math.max(robotX - 1, MIN_X);
                    newY = Math.max(robotY - 1, MIN_Y);
                }
                break;
        }

        // Check if movement is possible
        if (newX != robotX || newY != robotY) {
            // Update position and direction
            int oldX = robotX;
            int oldY = robotY;
            robotX = newX;
            robotY = newY;
            robotDirection = newDirection;

            if (listener != null) {
                listener.onRobotPositionChangedNoSend(robotX, robotY, robotDirection); // Use NoSend version
                listener.onRobotMoved(oldX, oldY, robotX, robotY, robotDirection);
                listener.onStatusMessage("Robot turned " + turnType + " from " +
                        "(" + oldX + "," + oldY + ") to (" + newX + "," + newY + "," + newDirection + ")");
            }
            return true;
        } else {
            if (listener != null) {
                listener.onStatusMessage("Robot cannot turn " + turnType + " - would hit boundary");
            }
            return false;
        }
    }

    // Helper methods for turning logic
    private String getTurnType(String currentDirection, String targetDirection) {
        // Determine if target direction is left, right, or 180-degree turn from current
        switch (currentDirection) {
            case "N":
                if (targetDirection.equals("E")) return "right";
                if (targetDirection.equals("W")) return "left";
                if (targetDirection.equals("S")) return "180";
                break;
            case "E":
                if (targetDirection.equals("S")) return "right";
                if (targetDirection.equals("N")) return "left";
                if (targetDirection.equals("W")) return "180";
                break;
            case "S":
                if (targetDirection.equals("W")) return "right";
                if (targetDirection.equals("E")) return "left";
                if (targetDirection.equals("N")) return "180";
                break;
            case "W":
                if (targetDirection.equals("N")) return "right";
                if (targetDirection.equals("S")) return "left";
                if (targetDirection.equals("E")) return "180";
                break;
        }
        return "none";
    }

    private String getLeftDirection(String currentDirection) {
        switch (currentDirection) {
            case "N": return "W";
            case "W": return "S";
            case "S": return "E";
            case "E": return "N";
            default: return currentDirection;
        }
    }

    private String getRightDirection(String currentDirection) {
        switch (currentDirection) {
            case "N": return "E";
            case "E": return "S";
            case "S": return "W";
            case "W": return "N";
            default: return currentDirection;
        }
    }

    // Getters
    public int getRobotX() {
        return robotX;
    }

    public int getRobotY() {
        return robotY;
    }

    public String getRobotDirection() {
        return robotDirection;
    }

    public String getRobotPositionString() {
        if (robotX == -1 && robotY == -1) {
            return "Off Grid (" + robotDirection + ")";
        }
        return "(" + robotX + ", " + robotY + ", " + robotDirection + ")";
    }

    // Validation - updated for 2x2 robot size
    private boolean isValidPosition(int x, int y) {
        if (x == -1 && y == -1) return true; // Off-grid position
        // Check that both the robot's position and its 2x2 footprint fit within bounds
        return (x >= MIN_X && x <= MAX_X - ROBOT_SIZE + 1 &&
                y >= MIN_Y && y <= MAX_Y - ROBOT_SIZE + 1);
    }

    private boolean isValidDirection(String direction) {
        return direction != null && (direction.equals("N") || direction.equals("S") ||
                direction.equals("E") || direction.equals("W"));
    }

    // Distance and Navigation Helpers
    public int getDistanceTo(int targetX, int targetY) {
        return Math.abs(robotX - targetX) + Math.abs(robotY - targetY);
    }

    public String getDirectionTo(int targetX, int targetY) {
        int deltaX = targetX - robotX;
        int deltaY = targetY - robotY;

        if (Math.abs(deltaX) > Math.abs(deltaY)) {
            return deltaX > 0 ? "E" : "W";
        } else {
            return deltaY > 0 ? "N" : "S";
        }
    }

    public boolean isAtPosition(int x, int y) {
        return robotX == x && robotY == y;
    }

    // Status
    public String getRobotStatus() {
        return "Robot Status: Position " + getRobotPositionString() +
                " | Can move: N=" + canMoveNorth() + " S=" + canMoveSouth() +
                " E=" + canMoveEast() + " W=" + canMoveWest();
    }

    private boolean canMoveNorth() {
        return robotY < MAX_Y - ROBOT_SIZE + 1;
    }

    private boolean canMoveSouth() {
        return robotY > MIN_Y;
    }

    private boolean canMoveEast() {
        return robotX < MAX_X - ROBOT_SIZE + 1;
    }

    private boolean canMoveWest() {
        return robotX > MIN_X;
    }
}