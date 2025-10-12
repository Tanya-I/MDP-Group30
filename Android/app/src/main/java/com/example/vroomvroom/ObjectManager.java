// ObjectManager.java
package com.example.vroomvroom;

import android.content.Context;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.TextView;

public class ObjectManager {

    public interface ObjectUpdateListener {
        void onObjectPositionChanged(String objectType, int x, int y, String direction);
        void onObjectDirectionChanged(String objectType, String direction);
        void onTargetUpdated(String objectType, int targetId);
        void onStatusMessage(String message);
    }

    private Context context;
    private ObjectUpdateListener listener;

    // Object position tracking - EXPANDED TO 8
    private int object1X = -1, object1Y = -1;
    private int object2X = -1, object2Y = -1;
    private int object3X = -1, object3Y = -1;
    private int object4X = -1, object4Y = -1;
    private int object5X = -1, object5Y = -1;
    private int object6X = -1, object6Y = -1;
    private int object7X = -1, object7Y = -1;
    private int object8X = -1, object8Y = -1;

    private boolean object1Placed = false;
    private boolean object2Placed = false;
    private boolean object3Placed = false;
    private boolean object4Placed = false;
    private boolean object5Placed = false;
    private boolean object6Placed = false;
    private boolean object7Placed = false;
    private boolean object8Placed = false;

    // Object direction tracking - EXPANDED TO 8
    private String object1Direction = "N";
    private String object2Direction = "N";
    private String object3Direction = "N";
    private String object4Direction = "N";
    private String object5Direction = "N";
    private String object6Direction = "N";
    private String object7Direction = "N";
    private String object8Direction = "N";

    // Object target ID tracking - EXPANDED TO 8
    private int object1TargetId = 1;
    private int object2TargetId = 2;
    private int object3TargetId = 3;
    private int object4TargetId = 4;
    private int object5TargetId = 5;
    private int object6TargetId = 6;
    private int object7TargetId = 7;
    private int object8TargetId = 8;

    // View references - EXPANDED TO 8
    private View object1DirectionView;
    private View object2DirectionView;
    private View object3DirectionView;
    private View object4DirectionView;
    private View object5DirectionView;
    private View object6DirectionView;
    private View object7DirectionView;
    private View object8DirectionView;

    private TextView object1TextView;
    private TextView object2TextView;
    private TextView object3TextView;
    private TextView object4TextView;
    private TextView object5TextView;
    private TextView object6TextView;
    private TextView object7TextView;
    private TextView object8TextView;

    public ObjectManager(Context context) {
        this.context = context;
    }

    public void setListener(ObjectUpdateListener listener) {
        this.listener = listener;
    }

    public void initializeViews(View rootView) {
        // Direction indicators
        object1DirectionView = rootView.findViewById(R.id.object1_direction);
        object2DirectionView = rootView.findViewById(R.id.object2_direction);
        object3DirectionView = rootView.findViewById(R.id.object3_direction);
        object4DirectionView = rootView.findViewById(R.id.object4_direction);
        object5DirectionView = rootView.findViewById(R.id.object5_direction);
        object6DirectionView = rootView.findViewById(R.id.object6_direction);
        object7DirectionView = rootView.findViewById(R.id.object7_direction);
        object8DirectionView = rootView.findViewById(R.id.object8_direction);

        // Text views
        object1TextView = rootView.findViewById(R.id.object1_number);
        object2TextView = rootView.findViewById(R.id.object2_number);
        object3TextView = rootView.findViewById(R.id.object3_number);
        object4TextView = rootView.findViewById(R.id.object4_number);
        object5TextView = rootView.findViewById(R.id.object5_number);
        object6TextView = rootView.findViewById(R.id.object6_number);
        object7TextView = rootView.findViewById(R.id.object7_number);
        object8TextView = rootView.findViewById(R.id.object8_number);

        initializeDirectionIndicators();
        updateAllTargetDisplays();
    }

    // Position Management
    public void setObjectPosition(String objectType, int x, int y) {
        switch (objectType) {
            case "OBJECT1":
                object1X = x;
                object1Y = y;
                object1Placed = (x != -1 && y != -1);
                break;
            case "OBJECT2":
                object2X = x;
                object2Y = y;
                object2Placed = (x != -1 && y != -1);
                break;
            case "OBJECT3":
                object3X = x;
                object3Y = y;
                object3Placed = (x != -1 && y != -1);
                break;
            case "OBJECT4":
                object4X = x;
                object4Y = y;
                object4Placed = (x != -1 && y != -1);
                break;
            case "OBJECT5":
                object5X = x;
                object5Y = y;
                object5Placed = (x != -1 && y != -1);
                break;
            case "OBJECT6":
                object6X = x;
                object6Y = y;
                object6Placed = (x != -1 && y != -1);
                break;
            case "OBJECT7":
                object7X = x;
                object7Y = y;
                object7Placed = (x != -1 && y != -1);
                break;
            case "OBJECT8":
                object8X = x;
                object8Y = y;
                object8Placed = (x != -1 && y != -1);
                break;
        }

        if (listener != null) {
            listener.onObjectPositionChanged(objectType, x, y, getObjectDirection(objectType));
        }
    }

    public void resetObjectPosition(String objectType) {
        setObjectPosition(objectType, -1, -1);
    }

    // Direction Management
    public void setObjectDirection(String objectType, String direction) {
        switch (objectType) {
            case "OBJECT1":
                object1Direction = direction;
                break;
            case "OBJECT2":
                object2Direction = direction;
                break;
            case "OBJECT3":
                object3Direction = direction;
                break;
            case "OBJECT4":
                object4Direction = direction;
                break;
            case "OBJECT5":
                object5Direction = direction;
                break;
            case "OBJECT6":
                object6Direction = direction;
                break;
            case "OBJECT7":
                object7Direction = direction;
                break;
            case "OBJECT8":
                object8Direction = direction;
                break;
        }

        updateDirectionIndicator(objectType, direction);

        if (listener != null) {
            listener.onObjectDirectionChanged(objectType, direction);
        }
    }

    public String getObjectDirection(String objectType) {
        switch (objectType) {
            case "OBJECT1":
                return object1Direction;
            case "OBJECT2":
                return object2Direction;
            case "OBJECT3":
                return object3Direction;
            case "OBJECT4":
                return object4Direction;
            case "OBJECT5":
                return object5Direction;
            case "OBJECT6":
                return object6Direction;
            case "OBJECT7":
                return object7Direction;
            case "OBJECT8":
                return object8Direction;
            default:
                return "N";
        }
    }

    // Target ID Management
    public void setObjectTargetId(String objectType, int targetId) {
        if (targetId < 1 || targetId > 40) {
            if (listener != null) {
                listener.onStatusMessage("Invalid target ID: " + targetId + ". Must be 1-40.");
            }
            return;
        }

        switch (objectType) {
            case "OBJECT1":
                object1TargetId = targetId;
                break;
            case "OBJECT2":
                object2TargetId = targetId;
                break;
            case "OBJECT3":
                object3TargetId = targetId;
                break;
            case "OBJECT4":
                object4TargetId = targetId;
                break;
            case "OBJECT5":
                object5TargetId = targetId;
                break;
            case "OBJECT6":
                object6TargetId = targetId;
                break;
            case "OBJECT7":
                object7TargetId = targetId;
                break;
            case "OBJECT8":
                object8TargetId = targetId;
                break;
        }

        updateTargetDisplay(objectType, targetId);

        if (listener != null) {
            listener.onTargetUpdated(objectType, targetId);
            listener.onStatusMessage("Object " + objectType + " target ID updated to: " + targetId);
        }
    }

    public int getObjectTargetId(String objectType) {
        switch (objectType) {
            case "OBJECT1":
                return object1TargetId;
            case "OBJECT2":
                return object2TargetId;
            case "OBJECT3":
                return object3TargetId;
            case "OBJECT4":
                return object4TargetId;
            case "OBJECT5":
                return object5TargetId;
            case "OBJECT6":
                return object6TargetId;
            case "OBJECT7":
                return object7TargetId;
            case "OBJECT8":
                return object8TargetId;
            default:
                return 1;
        }
    }

    // Position Getters
    public int getObjectX(String objectType) {
        switch (objectType) {
            case "OBJECT1":
                return object1X;
            case "OBJECT2":
                return object2X;
            case "OBJECT3":
                return object3X;
            case "OBJECT4":
                return object4X;
            case "OBJECT5":
                return object5X;
            case "OBJECT6":
                return object6X;
            case "OBJECT7":
                return object7X;
            case "OBJECT8":
                return object8X;
            default:
                return -1;
        }
    }

    public int getObjectY(String objectType) {
        switch (objectType) {
            case "OBJECT1":
                return object1Y;
            case "OBJECT2":
                return object2Y;
            case "OBJECT3":
                return object3Y;
            case "OBJECT4":
                return object4Y;
            case "OBJECT5":
                return object5Y;
            case "OBJECT6":
                return object6Y;
            case "OBJECT7":
                return object7Y;
            case "OBJECT8":
                return object8Y;
            default:
                return -1;
        }
    }

    public boolean isObjectPlaced(String objectType) {
        switch (objectType) {
            case "OBJECT1":
                return object1Placed;
            case "OBJECT2":
                return object2Placed;
            case "OBJECT3":
                return object3Placed;
            case "OBJECT4":
                return object4Placed;
            case "OBJECT5":
                return object5Placed;
            case "OBJECT6":
                return object6Placed;
            case "OBJECT7":
                return object7Placed;
            case "OBJECT8":
                return object8Placed;
            default:
                return false;
        }
    }

    // Visual Updates
    private void updateDirectionIndicator(String objectType, String direction) {
        View directionIndicator = getDirectionView(objectType);
        if (directionIndicator == null) return;

        FrameLayout.LayoutParams params = (FrameLayout.LayoutParams) directionIndicator.getLayoutParams();

        switch (direction) {
            case "N":
                params.width = dpToPx(20);
                params.height = dpToPx(3);
                params.gravity = android.view.Gravity.TOP | android.view.Gravity.CENTER_HORIZONTAL;
                params.setMargins(0, dpToPx(2), 0, 0);
                break;

            case "S":
                params.width = dpToPx(20);
                params.height = dpToPx(3);
                params.gravity = android.view.Gravity.BOTTOM | android.view.Gravity.CENTER_HORIZONTAL;
                params.setMargins(0, 0, 0, dpToPx(2));
                break;

            case "E":
                params.width = dpToPx(3);
                params.height = dpToPx(20);
                params.gravity = android.view.Gravity.RIGHT | android.view.Gravity.CENTER_VERTICAL;
                params.setMargins(0, 0, dpToPx(2), 0);
                break;

            case "W":
                params.width = dpToPx(3);
                params.height = dpToPx(20);
                params.gravity = android.view.Gravity.LEFT | android.view.Gravity.CENTER_VERTICAL;
                params.setMargins(dpToPx(2), 0, 0, 0);
                break;
        }

        directionIndicator.setLayoutParams(params);
    }

    private void updateTargetDisplay(String objectType, int targetId) {
        TextView textView = getTextView(objectType);
        if (textView != null) {
            textView.setText(String.valueOf(targetId));
            textView.setTextSize(android.util.TypedValue.COMPLEX_UNIT_SP, 14);
        }
    }

    private void initializeDirectionIndicators() {
        updateDirectionIndicator("OBJECT1", "N");
        updateDirectionIndicator("OBJECT2", "N");
        updateDirectionIndicator("OBJECT3", "N");
        updateDirectionIndicator("OBJECT4", "N");
        updateDirectionIndicator("OBJECT5", "N");
        updateDirectionIndicator("OBJECT6", "N");
        updateDirectionIndicator("OBJECT7", "N");
        updateDirectionIndicator("OBJECT8", "N");
    }

    private void updateAllTargetDisplays() {
        initializeTargetDisplay("OBJECT1", object1TargetId);
        initializeTargetDisplay("OBJECT2", object2TargetId);
        initializeTargetDisplay("OBJECT3", object3TargetId);
        initializeTargetDisplay("OBJECT4", object4TargetId);
        initializeTargetDisplay("OBJECT5", object5TargetId);
        initializeTargetDisplay("OBJECT6", object6TargetId);
        initializeTargetDisplay("OBJECT7", object7TargetId);
        initializeTargetDisplay("OBJECT8", object8TargetId);
    }

    private void initializeTargetDisplay(String objectType, int targetId) {
        TextView textView = getTextView(objectType);
        if (textView != null) {
            textView.setText(String.valueOf(targetId));
            textView.setTextSize(android.util.TypedValue.COMPLEX_UNIT_SP, 7);
        }
    }

    // Helper Methods
    private View getDirectionView(String objectType) {
        switch (objectType) {
            case "OBJECT1":
                return object1DirectionView;
            case "OBJECT2":
                return object2DirectionView;
            case "OBJECT3":
                return object3DirectionView;
            case "OBJECT4":
                return object4DirectionView;
            case "OBJECT5":
                return object5DirectionView;
            case "OBJECT6":
                return object6DirectionView;
            case "OBJECT7":
                return object7DirectionView;
            case "OBJECT8":
                return object8DirectionView;
            default:
                return null;
        }
    }

    private TextView getTextView(String objectType) {
        switch (objectType) {
            case "OBJECT1":
                return object1TextView;
            case "OBJECT2":
                return object2TextView;
            case "OBJECT3":
                return object3TextView;
            case "OBJECT4":
                return object4TextView;
            case "OBJECT5":
                return object5TextView;
            case "OBJECT6":
                return object6TextView;
            case "OBJECT7":
                return object7TextView;
            case "OBJECT8":
                return object8TextView;
            default:
                return null;
        }
    }

    private int dpToPx(int dp) {
        float density = context.getResources().getDisplayMetrics().density;
        return Math.round(dp * density);
    }

    // Status Methods
    public String getObjectStatus(String objectType) {
        int x = getObjectX(objectType);
        int y = getObjectY(objectType);
        String direction = getObjectDirection(objectType);
        int targetId = getObjectTargetId(objectType);

        if (isObjectPlaced(objectType)) {
            return objectType + " Target#" + targetId + ": (" + x + "," + y + "," + direction + ")";
        } else {
            return objectType + " Target#" + targetId + ": Not placed (" + direction + ")";
        }
    }

    public String getAllObjectsStatus() {
        StringBuilder status = new StringBuilder();
        status.append("Objects Status:\n");
        status.append(getObjectStatus("OBJECT1")).append("\n");
        status.append(getObjectStatus("OBJECT2")).append("\n");
        status.append(getObjectStatus("OBJECT3")).append("\n");
        status.append(getObjectStatus("OBJECT4")).append("\n");
        status.append(getObjectStatus("OBJECT5")).append("\n");
        status.append(getObjectStatus("OBJECT6")).append("\n");
        status.append(getObjectStatus("OBJECT7")).append("\n");
        status.append(getObjectStatus("OBJECT8"));
        return status.toString();
    }
}