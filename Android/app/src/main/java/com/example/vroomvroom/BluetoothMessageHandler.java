// BluetoothMessageHandler.java - Handles Bluetooth message formatting and parsing
package com.example.vroomvroom;

public class BluetoothMessageHandler {

    public interface BluetoothMessageListener {
        void onSendMessage(String message);
        void onStatusMessage(String message);
        void onTargetUpdate(String objectType, int targetId);
        void onRobotPositionUpdate(int x, int y, String direction);
        void onObjectPositionUpdate(String objectType, int x, int y, String direction);
        void onWeek8TaskDone(); // New callback for Week 8 task completion
        void onWeek9TaskDone(); // New callback for Week 9 task completion
    }

    private BluetoothMessageListener listener;

    public void setListener(BluetoothMessageListener listener) {
        this.listener = listener;
    }

    // Outgoing Message Formatting
    public void sendRobotPosition(int x, int y, String direction) {
        String message;
        if (x == -1 && y == -1) {
            message = "ROBOT, UNKNOWN";
        } else {
            message = "ROBOT, " + x + ", " + y + ", " + direction;
        }

        if (listener != null) {
            listener.onSendMessage(message);
            listener.onStatusMessage("Sent via Bluetooth: " + message);
        }
    }

    public void sendObjectPosition(String objectType, int x, int y, String direction) {
        String message;
        if (x == -1 && y == -1) {
            message = objectType + ", UNKNOWN";
        } else {
            message = objectType + ", " + x + ", " + y + ", " + direction;
        }

        if (listener != null) {
            listener.onSendMessage(message);
            listener.onStatusMessage("Sent via Bluetooth: " + message);
        }
    }

    public void sendRobotMovementCommand(String direction) {
        String command = "ROBOT " + direction.toUpperCase();

        if (listener != null) {
            listener.onSendMessage(command);
            listener.onStatusMessage("Movement command sent: " + command);
        }
    }

    public void sendChatMessage(String message) {
        if (message == null || message.trim().isEmpty()) {
            if (listener != null) {
                listener.onStatusMessage("Cannot send empty message");
            }
            return;
        }

        if (listener != null) {
            listener.onSendMessage(message.trim());
            listener.onStatusMessage("Chat sent: " + message.trim());
        }
    }

    public void sendCustomCommand(String command) {
        if (listener != null) {
            listener.onSendMessage(command);
            listener.onStatusMessage("Command sent: " + command);
        }
    }

    // Incoming Message Parsing
    public void handleIncomingMessage(String message) {
        if (message == null || message.trim().isEmpty()) {
            return;
        }

        String trimmedMessage = message.trim();

        if (listener != null) {
            listener.onStatusMessage("Received: " + trimmedMessage);
        }

        // Check for task completion messages first
        if (parseTaskCompletionMessage(trimmedMessage)) {
            return;
        }

        // Try to parse as TARGET message first
        if (parseTargetMessage(trimmedMessage)) {
            return;
        }

        // Try to parse as ROBOT position message
        if (parseRobotPositionMessage(trimmedMessage)) {
            return;
        }

        // Try to parse as OBJECT position message
        if (parseObjectPositionMessage(trimmedMessage)) {
            return;
        }

        // If not a recognized command format, treat as general message
        if (listener != null) {
            listener.onStatusMessage("General message received: " + trimmedMessage);
        }
    }

    // New method to parse task completion messages
    private boolean parseTaskCompletionMessage(String message) {
        String upperMessage = message.toUpperCase();

        if (upperMessage.equals("WEEK8_TASK_DONE")) {
            if (listener != null) {
                listener.onWeek8TaskDone();
                listener.onStatusMessage("Week 8 task completed!");
            }
            return true;
        }

        if (upperMessage.equals("WEEK9_TASK_DONE")) {
            if (listener != null) {
                listener.onWeek9TaskDone();
                listener.onStatusMessage("Week 9 task completed!");
            }
            return true;
        }

        return false;
    }

    private boolean parseTargetMessage(String message) {
        String[] parts = message.split(",");
        if (parts.length != 3) {
            return false;
        }

        String command = parts[0].trim().toUpperCase();
        if (!command.equals("TARGET")) {
            return false;
        }

        try {
            int obstacleNumber = Integer.parseInt(parts[1].trim());
            int targetId = Integer.parseInt(parts[2].trim());

            // Validate obstacle number (1-8)
            if (obstacleNumber < 1 || obstacleNumber > 8) {
                if (listener != null) {
                    listener.onStatusMessage("Invalid obstacle number: " + obstacleNumber + " (must be 1-8)");
                }
                return false;
            }

            // Validate target ID (1-40)
            if (targetId < 1 || targetId > 40) {
                if (listener != null) {
                    listener.onStatusMessage("Invalid target ID: " + targetId + " (must be 1-40)");
                }
                return false;
            }

            // Convert obstacle number to object type
            String objectType = "OBJECT" + obstacleNumber;

            if (listener != null) {
                listener.onTargetUpdate(objectType, targetId);
                listener.onStatusMessage("Target updated: " + objectType + " -> Target ID " + targetId);
            }

            return true;

        } catch (NumberFormatException e) {
            if (listener != null) {
                listener.onStatusMessage("Invalid TARGET message format: " + message);
            }
            return false;
        }
    }

    private boolean parseRobotPositionMessage(String message) {
        String[] parts = message.split(",");

        // Handle both "ROBOT, UNKNOWN" and "ROBOT, X, Y, DIRECTION" formats
        if (parts.length < 2) {
            return false;
        }

        String command = parts[0].trim().toUpperCase();
        if (!command.equals("ROBOT")) {
            return false;
        }

        // Handle "ROBOT, UNKNOWN" case
        if (parts.length == 2 && parts[1].trim().toUpperCase().equals("UNKNOWN")) {
            if (listener != null) {
                listener.onStatusMessage("Received robot position: UNKNOWN");
            }
            return true;
        }

        // Handle "ROBOT, X, Y, DIRECTION" case
        if (parts.length != 4) {
            if (listener != null) {
                listener.onStatusMessage("Invalid ROBOT message format: " + message + " (expected: ROBOT, X, Y, DIRECTION)");
            }
            return false;
        }

        try {
            int x = Integer.parseInt(parts[1].trim());
            int y = Integer.parseInt(parts[2].trim());
            String direction = parts[3].trim().toUpperCase();

            // Validate coordinates (0-19)
            if (x < 0 || x > 19 || y < 0 || y > 19) {
                if (listener != null) {
                    listener.onStatusMessage("Invalid robot coordinates: (" + x + "," + y + ") - must be 0-19");
                }
                return false;
            }

            // Validate direction
            if (!direction.equals("N") && !direction.equals("S") &&
                    !direction.equals("E") && !direction.equals("W")) {
                if (listener != null) {
                    listener.onStatusMessage("Invalid robot direction: " + direction + " (must be N, S, E, or W)");
                }
                return false;
            }

            if (listener != null) {
                listener.onRobotPositionUpdate(x, y, direction);
                listener.onStatusMessage("Robot position updated from Bluetooth: (" + x + "," + y + "," + direction + ")");
            }

            return true;

        } catch (NumberFormatException e) {
            if (listener != null) {
                listener.onStatusMessage("Invalid ROBOT message format - coordinates must be numbers: " + message);
            }
            return false;
        }
    }

    private boolean parseObjectPositionMessage(String message) {
        String[] parts = message.split(",");

        if (parts.length < 2) {
            return false;
        }

        String objectType = parts[0].trim().toUpperCase();

        // Check if it's a valid object type
        if (!objectType.equals("OBJECT1") && !objectType.equals("OBJECT2") &&
                !objectType.equals("OBJECT3") && !objectType.equals("OBJECT4") &&
                !objectType.equals("OBJECT5") && !objectType.equals("OBJECT6") &&
                !objectType.equals("OBJECT7") && !objectType.equals("OBJECT8"))  {
            return false;
        }

        // Handle "OBJECT#, UNKNOWN" case
        if (parts.length == 2 && parts[1].trim().toUpperCase().equals("UNKNOWN")) {
            if (listener != null) {
                listener.onStatusMessage("Received object position: " + objectType + " UNKNOWN");
            }
            return true;
        }

        // Handle "OBJECT#, X, Y, DIRECTION" case
        if (parts.length != 4) {
            if (listener != null) {
                listener.onStatusMessage("Invalid " + objectType + " message format: " + message + " (expected: " + objectType + ", X, Y, DIRECTION)");
            }
            return false;
        }

        try {
            int x = Integer.parseInt(parts[1].trim());
            int y = Integer.parseInt(parts[2].trim());
            String direction = parts[3].trim().toUpperCase();

            // Validate coordinates (0-19)
            if (x < 0 || x > 19 || y < 0 || y > 19) {
                if (listener != null) {
                    listener.onStatusMessage("Invalid " + objectType + " coordinates: (" + x + "," + y + ") - must be 0-19");
                }
                return false;
            }

            // Validate direction
            if (!direction.equals("N") && !direction.equals("S") &&
                    !direction.equals("E") && !direction.equals("W")) {
                if (listener != null) {
                    listener.onStatusMessage("Invalid " + objectType + " direction: " + direction + " (must be N, S, E, or W)");
                }
                return false;
            }

            if (listener != null) {
                listener.onObjectPositionUpdate(objectType, x, y, direction);
                listener.onStatusMessage("Object position updated from Bluetooth: " + objectType + " (" + x + "," + y + "," + direction + ")");
            }

            return true;

        } catch (NumberFormatException e) {
            if (listener != null) {
                listener.onStatusMessage("Invalid " + objectType + " message format - coordinates must be numbers: " + message);
            }
            return false;
        }
    }

    // Message Validation
    public boolean isValidPositionMessage(String itemType, int x, int y, String direction) {
        if (itemType == null || itemType.trim().isEmpty()) {
            return false;
        }

        if (x < -1 || x > 19 || y < -1 || y > 19) {
            return false;
        }

        if (direction == null || (!direction.equals("N") && !direction.equals("S") &&
                !direction.equals("E") && !direction.equals("W"))) {
            return false;
        }

        String upperItemType = itemType.toUpperCase();
        return upperItemType.equals("ROBOT") ||
                upperItemType.equals("OBJECT1") ||
                upperItemType.equals("OBJECT2") ||
                upperItemType.equals("OBJECT3") ||
                upperItemType.equals("OBJECT4") ||
                upperItemType.equals("OBJECT5") ||
                upperItemType.equals("OBJECT6") ||
                upperItemType.equals("OBJECT7") ||
                upperItemType.equals("OBJECT8")
                ;
    }

    public boolean isValidTargetMessage(int obstacleNumber, int targetId) {
        return (obstacleNumber >= 1 && obstacleNumber <= 8) && (targetId >= 1 && targetId <= 40);
    }

    // Status and Debug Methods
    public String formatDebugMessage(String prefix, String content) {
        return "[" + prefix + "] " + content;
    }

    public String formatErrorMessage(String error) {
        return "ERROR: " + error;
    }

    public String formatConnectionStatus(boolean connected, String deviceName) {
        if (connected) {
            return "Connected to: " + deviceName;
        } else {
            return "Disconnected" + (deviceName != null ? " from " + deviceName : "");
        }
    }
}