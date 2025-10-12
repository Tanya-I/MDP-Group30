// MainActivity.java
package com.example.vroomvroom;

import android.app.AlertDialog;
import android.bluetooth.BluetoothDevice;
import android.os.Bundle;
import android.os.Handler;
import android.os.SystemClock;
import android.text.method.ScrollingMovementMethod;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TableLayout;
import android.widget.TableRow;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;

public class MainActivity extends AppCompatActivity implements
        DragDropManager.OnDragEventListener,
        BluetoothManager.BluetoothListener,
        ObjectManager.ObjectUpdateListener,
        RobotManager.RobotUpdateListener,
        BluetoothMessageHandler.BluetoothMessageListener,
        DirectionSelectionDialog.OnDirectionSelectedListener {

    private static final String TAG = "MainActivity";

    // UI Components
    private TextView connectedDevice;
    private View connectionIndicator;
    private Button connectButton;
    private TextView robotPositionValue;
    private TextView objectPlacementValue;
    private TextView messageBox;
    private CustomGridView customGrid;
    private Button clearPathButton;

    // Directional buttons
    private Button btnUp;
    private Button btnDown;
    private Button btnLeft;
    private Button btnRight;

    // UI elements
    private Button wk8Button;
    private TextView wk8Timer;
    private Button wk9Button;
    private TextView wk9Timer;

    private Button gridCompleteButton;
    private EditText chatBox;
    private Button sendButton;
    private TableLayout coordinateGrid;

    // Object views - EXPANDED TO 8
    private View object1, object2, object3, object4, object5, object6, object7, object8;
    private View robotCar;
    private TextView coordPreview;

    // Manager instances
    private DragDropManager dragDropManager;
    private BluetoothManager bluetoothManager;
    private ObjectManager objectManager;
    private RobotManager robotManager;
    private BluetoothMessageHandler messageHandler;
    private DirectionSelectionDialog directionDialog;

    // Timer functionality
    private Handler timerHandler = new Handler();
    private Runnable week8TimerRunnable;
    private Runnable week9TimerRunnable;
    private long week8StartTime = 0;
    private long week9StartTime = 0;
    private boolean week8Running = false;
    private boolean week9Running = false;
    private long week8PausedTime = 0;
    private long week9PausedTime = 0;

    // State
    private String currentObject = "None";
    private float[] object1OriginalPos = new float[2];
    private float[] object2OriginalPos = new float[2];
    private float[] object3OriginalPos = new float[2];
    private float[] object4OriginalPos = new float[2];
    private float[] object5OriginalPos = new float[2];
    private float[] object6OriginalPos = new float[2];
    private float[] object7OriginalPos = new float[2];
    private float[] object8OriginalPos = new float[2];
    private float[] robotCarOriginalPos = new float[2];

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        initializeManagers();
        initViews();
        setupListeners();
        setupInitialState();
        setupTimerRunnables();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        bluetoothManager.cleanup();
        if (directionDialog != null) {
            directionDialog.dismiss();
        }
        timerHandler.removeCallbacks(week8TimerRunnable);
        timerHandler.removeCallbacks(week9TimerRunnable);
    }

    private void initializeManagers() {
        dragDropManager = new DragDropManager();
        dragDropManager.setEventListener(this);

        bluetoothManager = new BluetoothManager(this);
        bluetoothManager.setListener(this);

        objectManager = new ObjectManager(this);
        objectManager.setListener(this);

        robotManager = new RobotManager();
        robotManager.setListener(this);

        messageHandler = new BluetoothMessageHandler();
        messageHandler.setListener(this);

        directionDialog = new DirectionSelectionDialog(this);
        directionDialog.setOnDirectionSelectedListener(this);
    }

    private void setupTimerRunnables() {
        week8TimerRunnable = new Runnable() {
            @Override
            public void run() {
                if (week8Running) {
                    long elapsedTime = SystemClock.elapsedRealtime() - week8StartTime;
                    updateTimerDisplay(wk8Timer, elapsedTime);
                    timerHandler.postDelayed(this, 100);
                }
            }
        };

        week9TimerRunnable = new Runnable() {
            @Override
            public void run() {
                if (week9Running) {
                    long elapsedTime = SystemClock.elapsedRealtime() - week9StartTime;
                    updateTimerDisplay(wk9Timer, elapsedTime);
                    timerHandler.postDelayed(this, 100);
                }
            }
        };
    }

    private void updateTimerDisplay(TextView timerView, long elapsedTime) {
        long minutes = (elapsedTime / 1000) / 60;
        long seconds = (elapsedTime / 1000) % 60;
        long centiseconds = (elapsedTime % 1000) / 10;
        String timeString = String.format("%02d:%02d.%02d", minutes, seconds, centiseconds);
        timerView.setText(timeString);
    }

    private void startWeek8Timer() {
        if (!week8Running) {
            week8Running = true;
            week8StartTime = SystemClock.elapsedRealtime() - week8PausedTime;
            wk8Button.setEnabled(true);
            wk8Button.setText("Stop");
            timerHandler.post(week8TimerRunnable);
            appendMessage("Week 8 task started - Timer running");
        }
    }

    private void pauseWeek8Timer() {
        if (week8Running) {
            week8Running = false;
            week8PausedTime = SystemClock.elapsedRealtime() - week8StartTime;
            timerHandler.removeCallbacks(week8TimerRunnable);
            long minutes = (week8PausedTime / 1000) / 60;
            long seconds = (week8PausedTime / 1000) % 60;
            long centiseconds = (week8PausedTime % 1000) / 10;
            appendMessage(String.format("Week 8 task completed in %02d:%02d.%02d",
                    minutes, seconds, centiseconds));
        }
    }

    private void resetWeek8Timer() {
        week8Running = false;
        week8PausedTime = 0;
        timerHandler.removeCallbacks(week8TimerRunnable);
        wk8Button.setEnabled(true);
        wk8Button.setText("Start Week 8");
        wk8Timer.setText("00:00.00");
        appendMessage("Week 8 timer reset");
    }

    private void startWeek9Timer() {
        if (!week9Running) {
            week9Running = true;
            week9StartTime = SystemClock.elapsedRealtime() - week9PausedTime;
            wk9Button.setEnabled(true);
            wk9Button.setText("Stop");
            timerHandler.post(week9TimerRunnable);
            appendMessage("Week 9 task started - Timer running");
        }
    }

    private void pauseWeek9Timer() {
        if (week9Running) {
            week9Running = false;
            week9PausedTime = SystemClock.elapsedRealtime() - week9StartTime;
            timerHandler.removeCallbacks(week9TimerRunnable);
            long minutes = (week9PausedTime / 1000) / 60;
            long seconds = (week9PausedTime / 1000) % 60;
            long centiseconds = (week9PausedTime % 1000) / 10;
            appendMessage(String.format("Week 9 task completed in %02d:%02d.%02d",
                    minutes, seconds, centiseconds));
        }
    }

    private void resetWeek9Timer() {
        week9Running = false;
        week9PausedTime = 0;
        timerHandler.removeCallbacks(week9TimerRunnable);
        wk9Button.setEnabled(true);
        wk9Button.setText("Week 9");
        wk9Timer.setText("00:00.00");
        appendMessage("Week 9 timer reset");
    }

    private void showWeek8StopConfirmation() {
        new AlertDialog.Builder(this)
                .setTitle("Stop Week 8 Timer")
                .setMessage("Are you sure you want to stop and reset the Week 8 timer?")
                .setPositiveButton("Stop & Reset", (dialog, which) -> resetWeek8Timer())
                .setNegativeButton("Cancel", null)
                .show();
    }

    private void showWeek9StopConfirmation() {
        new AlertDialog.Builder(this)
                .setTitle("Stop Week 9 Timer")
                .setMessage("Are you sure you want to stop and reset the Week 9 timer?")
                .setPositiveButton("Stop & Reset", (dialog, which) -> resetWeek9Timer())
                .setNegativeButton("Cancel", null)
                .show();
    }

    private void startWeek8Task() {
        if (!week8Running) {
            messageHandler.sendCustomCommand("WEEK8_COMMAND");
            startWeek8Timer();
        } else {
            showWeek8StopConfirmation();
        }
    }

    private void startWeek9Task() {
        if (!week9Running) {
            messageHandler.sendCustomCommand("WEEK9_COMMAND");
            startWeek9Timer();
        } else {
            showWeek9StopConfirmation();
        }
    }

    private void initViews() {
        connectedDevice = findViewById(R.id.connected_device);
        connectionIndicator = findViewById(R.id.connection_indicator);
        connectButton = findViewById(R.id.connect);
        robotPositionValue = findViewById(R.id.robot_position_value);
        objectPlacementValue = findViewById(R.id.object_placement_value);
        messageBox = findViewById(R.id.message_box_card);
        chatBox = findViewById(R.id.chat_box_card);
        sendButton = findViewById(R.id.send_button);

        btnUp = findViewById(R.id.btn_up);
        btnDown = findViewById(R.id.btn_down);
        btnLeft = findViewById(R.id.btn_left);
        btnRight = findViewById(R.id.btn_right);

        wk8Button = findViewById(R.id.wk8button);
        wk8Timer = findViewById(R.id.wk8timer);
        wk9Button = findViewById(R.id.wk9button);
        wk9Timer = findViewById(R.id.wk9timer);
        gridCompleteButton = findViewById(R.id.gridCompleteButton);

        // EXPANDED TO 8 OBJECTS
        object1 = findViewById(R.id.object1);
        object2 = findViewById(R.id.object2);
        object3 = findViewById(R.id.object3);
        object4 = findViewById(R.id.object4);
        object5 = findViewById(R.id.object5);
        object6 = findViewById(R.id.object6);
        object7 = findViewById(R.id.object7);
        object8 = findViewById(R.id.object8);

        robotCar = findViewById(R.id.robot_car);
        coordPreview = findViewById(R.id.coord_preview);
        customGrid = findViewById(R.id.grid);
        coordinateGrid = findViewById(R.id.coordinate_grid);
        clearPathButton = findViewById(R.id.clear_path_button);

        objectManager.initializeViews(findViewById(R.id.MainFragment));

        messageBox.setMovementMethod(new ScrollingMovementMethod());
    }

    private void setupListeners() {
        connectButton.setOnClickListener(v -> {
            if (!bluetoothManager.isConnected()) {
                showBluetoothDiscovery();
            } else {
                bluetoothManager.disconnect();
            }
        });

        robotPositionValue.setOnClickListener(v -> {});
        objectPlacementValue.setOnClickListener(v -> {
            if (!currentObject.equals("None")) {
                showCoordinatePreview(currentObject);
            }
        });

        clearPathButton.setOnClickListener(v -> clearRobotPath());

        btnUp.setOnClickListener(v -> {
            messageHandler.sendRobotMovementCommand("FORWARD");
            if (robotManager.moveRobotInDirection("N")) {}
        });

        btnDown.setOnClickListener(v -> {
            messageHandler.sendRobotMovementCommand("BACK");
            if (robotManager.moveRobotInDirection("S")) {}
        });

        btnLeft.setOnClickListener(v -> {
            messageHandler.sendRobotMovementCommand("LEFT");
            if (robotManager.moveRobotInDirection("W")) {}
        });

        btnRight.setOnClickListener(v -> {
            messageHandler.sendRobotMovementCommand("RIGHT");
            if (robotManager.moveRobotInDirection("E")) {}
        });

        sendButton.setOnClickListener(v -> sendChatMessage());

        wk8Button.setOnClickListener(v -> startWeek8Task());
        wk9Button.setOnClickListener(v -> startWeek9Task());
        gridCompleteButton.setOnClickListener(v -> {
            messageHandler.sendCustomCommand("GRID_COMPLETE");
            appendMessage("Grid Complete command sent");
        });

        setupDragAndDrop();
    }

    private void setupInitialState() {
        setupCoordinateLabels();
        storeOriginalPositions();
        setupCustomGrid();
        updateConnectionStatus();
        updateRobotPosition();
        rotateRobotCarToDirection(robotManager.getRobotDirection());
        updateObjectPlacement();
        checkBluetoothSupport();

        wk8Timer.setText("00:00.00");
        wk9Timer.setText("00:00.00");
    }

    private void setupDragAndDrop() {
        robotCar.setOnTouchListener(dragDropManager.createDragTouchListener("CAR"));
        object1.setOnTouchListener(dragDropManager.createDragTouchListener("OBJECT1"));
        object2.setOnTouchListener(dragDropManager.createDragTouchListener("OBJECT2"));
        object3.setOnTouchListener(dragDropManager.createDragTouchListener("OBJECT3"));
        object4.setOnTouchListener(dragDropManager.createDragTouchListener("OBJECT4"));
        object5.setOnTouchListener(dragDropManager.createDragTouchListener("OBJECT5"));
        object6.setOnTouchListener(dragDropManager.createDragTouchListener("OBJECT6"));
        object7.setOnTouchListener(dragDropManager.createDragTouchListener("OBJECT7"));
        object8.setOnTouchListener(dragDropManager.createDragTouchListener("OBJECT8"));
    }

    private void clearRobotPath() {
        customGrid.clearPath();
    }

    private void setupCustomGrid() {
        customGrid.setTableLayoutReference(coordinateGrid);
        customGrid.setRobotPosition(robotManager.getRobotX(), robotManager.getRobotY());
        dragDropManager.setTargetGrid(customGrid);
        customGrid.bringToFront();
    }

    private void setupCoordinateLabels() {
        coordinateGrid.removeAllViews();

        for (int y = 19; y >= 0; y--) {
            TableRow dataRow = new TableRow(this);
            dataRow.setLayoutParams(new TableLayout.LayoutParams(
                    TableLayout.LayoutParams.MATCH_PARENT,
                    0, 1.0f));

            TextView yLabel = createCoordinateCell(String.valueOf(y));
            yLabel.setBackgroundColor(0xFFF0F0F0);
            dataRow.addView(yLabel);

            for (int x = 0; x < 20; x++) {
                TextView gridCell = createCoordinateCell("");
                gridCell.setBackgroundColor(0x00000000);
                dataRow.addView(gridCell);
            }

            coordinateGrid.addView(dataRow);
        }

        TableRow bottomRow = new TableRow(this);
        bottomRow.setLayoutParams(new TableLayout.LayoutParams(
                TableLayout.LayoutParams.MATCH_PARENT,
                0, 1.0f));

        TextView cornerCell = createCoordinateCell("");
        cornerCell.setBackgroundColor(0xFFE8E8E8);
        bottomRow.addView(cornerCell);

        for (int x = 0; x < 20; x++) {
            TextView xLabel = createCoordinateCell(String.valueOf(x));
            xLabel.setBackgroundColor(0xFFF0F0F0);
            bottomRow.addView(xLabel);
        }
        coordinateGrid.addView(bottomRow);
    }

    private TextView createCoordinateCell(String text) {
        TextView cell = new TextView(this);
        cell.setText(text);
        cell.setTextColor(0xFF666666);
        cell.setTextSize(android.util.TypedValue.COMPLEX_UNIT_SP, 10);
        cell.setGravity(android.view.Gravity.CENTER);
        cell.setPadding(1, 1, 1, 1);

        TableRow.LayoutParams params = new TableRow.LayoutParams(
                0, TableRow.LayoutParams.MATCH_PARENT, 1.0f);
        cell.setLayoutParams(params);

        return cell;
    }

    // BLUETOOTH MANAGER CALLBACKS
    @Override
    public void onConnectionStatusChanged(boolean connected, String deviceName) {
        runOnUiThread(() -> updateConnectionStatus());
    }

    @Override
    public void onConnectionAttemptStarted(String deviceName) {
        runOnUiThread(() -> {
            connectButton.setEnabled(false);
            connectButton.setText("Connecting...");
        });
    }

    @Override
    public void onConnectionFailed(String errorMessage) {
        runOnUiThread(() -> {
            connectButton.setEnabled(true);
            connectButton.setText("Connect");
            showAlert("Connection Failed", "Could not connect to the Bluetooth device. Make sure the device is on and in range.");
        });
    }

    @Override
    public void onMessageReceived(String message) {
        runOnUiThread(() -> messageHandler.handleIncomingMessage(message));
    }

    @Override
    public void onStatusMessage(String message) {
        runOnUiThread(() -> appendMessage(message));
    }

    @Override
    public void onPermissionDenied() {
        runOnUiThread(() -> handlePermissionDenied());
    }

    @Override
    public void onBluetoothDisabled() {
        runOnUiThread(() -> handleBluetoothDisabled());
    }

    // OBJECT MANAGER CALLBACKS
    @Override
    public void onObjectPositionChanged(String objectType, int x, int y, String direction) {
        messageHandler.sendObjectPosition(objectType, x, y, direction);
        updateObjectPlacement();
    }

    @Override
    public void onObjectDirectionChanged(String objectType, String direction) {
        if (objectManager.isObjectPlaced(objectType)) {
            messageHandler.sendObjectPosition(objectType,
                    objectManager.getObjectX(objectType),
                    objectManager.getObjectY(objectType),
                    direction);
        } else {
            messageHandler.sendObjectPosition(objectType, -1, -1, direction);
        }
        updateObjectPlacement();
    }

    @Override
    public void onTargetUpdated(String objectType, int targetId) {
        appendMessage("Target updated: " + objectType + " → Target ID " + targetId);
    }

    // ROBOT MANAGER CALLBACKS
    @Override
    public void onRobotMoved(int oldX, int oldY, int newX, int newY, String direction) {
        moveViewToGridCell(robotCar, newX, newY);
    }

    // BLUETOOTH MESSAGE HANDLER CALLBACKS
    @Override
    public void onSendMessage(String message) {
        if (bluetoothManager.isConnected()) {
            bluetoothManager.sendMessage(message);
        } else {
            appendMessage("Not connected - Message not sent: " + message);
        }
    }

    @Override
    public void onTargetUpdate(String objectType, int targetId) {
        objectManager.setObjectTargetId(objectType, targetId);
    }

    @Override
    public void onObjectPositionUpdate(String objectType, int x, int y, String direction) {
        objectManager.setObjectPosition(objectType, x, y);
        objectManager.setObjectDirection(objectType, direction);
        appendMessage("Received position update: " + objectType + " at (" + x + "," + y + "," + direction + ")");
    }

    @Override
    public void onWeek8TaskDone() {
        runOnUiThread(() -> pauseWeek8Timer());
    }

    @Override
    public void onWeek9TaskDone() {
        runOnUiThread(() -> pauseWeek9Timer());
    }

    private void rotateRobotCarToDirection(String direction) {
        float targetRotation = 0f;

        switch (direction) {
            case "N": targetRotation = 0f; break;
            case "E": targetRotation = 90f; break;
            case "S": targetRotation = 180f; break;
            case "W": targetRotation = 270f; break;
        }

        robotCar.animate()
                .rotation(targetRotation)
                .setDuration(50)
                .start();
    }

    @Override
    public void onRobotPositionChanged(int x, int y, String direction) {
        updateRobotPosition();
        customGrid.setRobotPosition(x, y);
        rotateRobotCarToDirection(direction);
        messageHandler.sendRobotPosition(x, y, direction);
    }

    @Override
    public void onRobotPositionChangedNoSend(int x, int y, String direction) {
        updateRobotPosition();
        customGrid.setRobotPosition(x, y);
        rotateRobotCarToDirection(direction);
    }

    @Override
    public void onRobotPositionUpdate(int x, int y, String direction) {
        robotManager.setRobotPositionFromBluetooth(x, y, direction);

        if (x >= 0 && y >= 0) {
            moveViewToGridCell(robotCar, x, y);
            customGrid.setRobotPosition(x, y);
        }

        rotateRobotCarToDirection(direction);
        appendMessage("Received robot update from Bluetooth: (" + x + "," + y + "," + direction + ")");
    }

    // DIRECTION DIALOG CALLBACKS
    @Override
    public void onDirectionSelected(String itemName, String direction) {
        if (itemName.equals("Robot Car")) {
            robotManager.setRobotDirection(direction);
            rotateRobotCarToDirection(direction);
        } else {
            String objectType = getObjectTypeFromDisplayName(itemName);
            if (objectType != null) {
                objectManager.setObjectDirection(objectType, direction);
            }
        }
    }

    @Override
    public void onDirectionCancelled(String itemName) {}

    // DRAG DROP CALLBACKS
    @Override
    public void onDragMessage(String message) {}

    @Override
    public void onItemDropped(String itemName, float x, float y) {
        switch (itemName) {
            case "OBJECT1":
                returnObjectToOriginalPosition(object1, object1OriginalPos, "Object 1");
                objectManager.resetObjectPosition("OBJECT1");
                break;
            case "OBJECT2":
                returnObjectToOriginalPosition(object2, object2OriginalPos, "Object 2");
                objectManager.resetObjectPosition("OBJECT2");
                break;
            case "OBJECT3":
                returnObjectToOriginalPosition(object3, object3OriginalPos, "Object 3");
                objectManager.resetObjectPosition("OBJECT3");
                break;
            case "OBJECT4":
                returnObjectToOriginalPosition(object4, object4OriginalPos, "Object 4");
                objectManager.resetObjectPosition("OBJECT4");
                break;
            case "OBJECT5":
                returnObjectToOriginalPosition(object5, object5OriginalPos, "Object 5");
                objectManager.resetObjectPosition("OBJECT5");
                break;
            case "OBJECT6":
                returnObjectToOriginalPosition(object6, object6OriginalPos, "Object 6");
                objectManager.resetObjectPosition("OBJECT6");
                break;
            case "OBJECT7":
                returnObjectToOriginalPosition(object7, object7OriginalPos, "Object 7");
                objectManager.resetObjectPosition("OBJECT7");
                break;
            case "OBJECT8":
                returnObjectToOriginalPosition(object8, object8OriginalPos, "Object 8");
                objectManager.resetObjectPosition("OBJECT8");
                break;
            case "CAR":
                returnObjectToOriginalPosition(robotCar, robotCarOriginalPos, "Robot Car");
                robotManager.setRobotPosition(-1, -1);
                customGrid.setRobotPosition(-1, -1);
                messageHandler.sendRobotPosition(-1, -1, robotManager.getRobotDirection());
                break;
        }
        updateObjectPlacement();
    }

    @Override
    public void onGridItemDropped(String itemName, int gridX, int gridY) {
        switch (itemName) {
            case "CAR":
                robotManager.setRobotPosition(gridX, gridY);
                moveViewToGridCell(robotCar, gridX, gridY);
                customGrid.setRobotPosition(gridX, gridY);
                break;
            case "OBJECT1":
                objectManager.setObjectPosition("OBJECT1", gridX, gridY);
                currentObject = "Object 1";
                moveViewToGridCell(object1, gridX, gridY);
                break;
            case "OBJECT2":
                objectManager.setObjectPosition("OBJECT2", gridX, gridY);
                currentObject = "Object 2";
                moveViewToGridCell(object2, gridX, gridY);
                break;
            case "OBJECT3":
                objectManager.setObjectPosition("OBJECT3", gridX, gridY);
                currentObject = "Object 3";
                moveViewToGridCell(object3, gridX, gridY);
                break;
            case "OBJECT4":
                objectManager.setObjectPosition("OBJECT4", gridX, gridY);
                currentObject = "Object 4";
                moveViewToGridCell(object4, gridX, gridY);
                break;
            case "OBJECT5":
                objectManager.setObjectPosition("OBJECT5", gridX, gridY);
                currentObject = "Object 5";
                moveViewToGridCell(object5, gridX, gridY);
                break;
            case "OBJECT6":
                objectManager.setObjectPosition("OBJECT6", gridX, gridY);
                currentObject = "Object 6";
                moveViewToGridCell(object6, gridX, gridY);
                break;
            case "OBJECT7":
                objectManager.setObjectPosition("OBJECT7", gridX, gridY);
                currentObject = "Object 7";
                moveViewToGridCell(object7, gridX, gridY);
                break;
            case "OBJECT8":
                objectManager.setObjectPosition("OBJECT8", gridX, gridY);
                currentObject = "Object 8";
                moveViewToGridCell(object8, gridX, gridY);
                break;
        }
        updateObjectPlacement();
    }

    @Override
    public void onItemSingleClick(String itemName) {
        switch (itemName) {
            case "OBJECT1":
                currentObject = "Object 1";
                updateObjectPlacement();
                break;
            case "OBJECT2":
                currentObject = "Object 2";
                updateObjectPlacement();
                break;
            case "OBJECT3":
                currentObject = "Object 3";
                updateObjectPlacement();
                break;
            case "OBJECT4":
                currentObject = "Object 4";
                updateObjectPlacement();
                break;
            case "OBJECT5":
                currentObject = "Object 5";
                updateObjectPlacement();
                break;
            case "OBJECT6":
                currentObject = "Object 6";
                updateObjectPlacement();
                break;
            case "OBJECT7":
                currentObject = "Object 7";
                updateObjectPlacement();
                break;
            case "OBJECT8":
                currentObject = "Object 8";
                updateObjectPlacement();
                break;
            case "CAR":
                showCoordinatePreview(robotManager.getRobotPositionString());
                break;
        }
    }

    @Override
    public void onItemDoubleClick(String itemName) {
        String displayName = getDisplayNameFromItemName(itemName);
        directionDialog.showDirectionDialog(displayName, itemName);
    }

    // HELPER METHODS
    private void updateConnectionStatus() {
        if (bluetoothManager.isConnected()) {
            connectionIndicator.setBackgroundColor(0xFF4CAF50);
            connectedDevice.setText("Connected: " + bluetoothManager.getConnectedDeviceName());
            connectButton.setText("Disconnect");
            connectButton.setEnabled(true);
        } else {
            connectionIndicator.setBackgroundColor(0xFFFF0000);
            connectedDevice.setText("No Device Connected");
            connectButton.setText("Connect");
            connectButton.setEnabled(true);
        }
    }

    private void updateRobotPosition() {
        robotPositionValue.setText(robotManager.getRobotPositionString());
    }

    private void updateObjectPlacement() {
        if (currentObject.equals("None")) {
            objectPlacementValue.setText("None");
        } else {
            String objectType = getObjectTypeFromDisplayName(currentObject);
            if (objectType != null && objectManager.isObjectPlaced(objectType)) {
                String direction = objectManager.getObjectDirection(objectType);
                objectPlacementValue.setText(currentObject + ": (" +
                        objectManager.getObjectX(objectType) + "," +
                        objectManager.getObjectY(objectType) + "," +
                        direction + ")");
            } else if (objectType != null) {
                String direction = objectManager.getObjectDirection(objectType);
                objectPlacementValue.setText(currentObject + ": Not placed (" + direction + ")");
            } else {
                objectPlacementValue.setText(currentObject);
            }
        }
    }

    private void sendChatMessage() {
        String message = chatBox.getText().toString().trim();
        if (!message.isEmpty()) {
            messageHandler.sendChatMessage(message);
            chatBox.setText("");
        }
    }

    private void moveViewToGridCell(View view, int gridX, int gridY) {
        float[] cellPosition = customGrid.getCellPosition(gridX, gridY);
        if (cellPosition != null) {
            int[] gridLocation = new int[2];
            customGrid.getLocationOnScreen(gridLocation);

            int[] mainLocation = new int[2];
            findViewById(R.id.MainFragment).getLocationOnScreen(mainLocation);

            float targetX, targetY;

            if (view == robotCar) {
                targetX = (gridLocation[0] - mainLocation[0]) + cellPosition[0];
                targetY = (gridLocation[1] - mainLocation[1]) + cellPosition[1] + cellPosition[3] - view.getHeight();
            } else {
                float centerX = cellPosition[0] + cellPosition[2] / 2.0f;
                float centerY = cellPosition[1] + cellPosition[3] / 2.0f;
                targetX = (gridLocation[0] - mainLocation[0]) + centerX - (view.getWidth() / 2.0f);
                targetY = (gridLocation[1] - mainLocation[1]) + centerY - (view.getHeight() / 2.0f);
            }

            view.animate()
                    .x(targetX)
                    .y(targetY)
                    .setDuration(50)
                    .start();
        }
    }

    private void returnObjectToOriginalPosition(View objectView, float[] originalPos, String objectName) {
        objectView.animate()
                .x(originalPos[0])
                .y(originalPos[1])
                .setDuration(300)
                .start();
    }

    private void storeOriginalPositions() {
        object1.post(() -> {
            object1OriginalPos[0] = object1.getX();
            object1OriginalPos[1] = object1.getY();
        });
        object2.post(() -> {
            object2OriginalPos[0] = object2.getX();
            object2OriginalPos[1] = object2.getY();
        });
        object3.post(() -> {
            object3OriginalPos[0] = object3.getX();
            object3OriginalPos[1] = object3.getY();
        });
        object4.post(() -> {
            object4OriginalPos[0] = object4.getX();
            object4OriginalPos[1] = object4.getY();
        });
        object5.post(() -> {
            object5OriginalPos[0] = object5.getX();
            object5OriginalPos[1] = object5.getY();
        });
        object6.post(() -> {
            object6OriginalPos[0] = object6.getX();
            object6OriginalPos[1] = object6.getY();
        });
        object7.post(() -> {
            object7OriginalPos[0] = object7.getX();
            object7OriginalPos[1] = object7.getY();
        });
        object8.post(() -> {
            object8OriginalPos[0] = object8.getX();
            object8OriginalPos[1] = object8.getY();
        });
        robotCar.post(() -> {
            robotCarOriginalPos[0] = robotCar.getX();
            robotCarOriginalPos[1] = robotCar.getY();
        });
    }

    private String getDisplayNameFromItemName(String itemName) {
        switch (itemName) {
            case "OBJECT1": return "Object 1";
            case "OBJECT2": return "Object 2";
            case "OBJECT3": return "Object 3";
            case "OBJECT4": return "Object 4";
            case "OBJECT5": return "Object 5";
            case "OBJECT6": return "Object 6";
            case "OBJECT7": return "Object 7";
            case "OBJECT8": return "Object 8";
            case "CAR": return "Robot Car";
            default: return itemName;
        }
    }

    private String getObjectTypeFromDisplayName(String displayName) {
        switch (displayName) {
            case "Object 1": return "OBJECT1";
            case "Object 2": return "OBJECT2";
            case "Object 3": return "OBJECT3";
            case "Object 4": return "OBJECT4";
            case "Object 5": return "OBJECT5";
            case "Object 6": return "OBJECT6";
            case "Object 7": return "OBJECT7";
            case "Object 8": return "OBJECT8";
            default: return null;
        }
    }

    private void showBluetoothDiscovery() {
        BluetoothDiscoveryFragment bluetoothFragment = BluetoothDiscoveryFragment.newInstance();
        bluetoothFragment.show(getSupportFragmentManager(), "bluetooth_discovery");
    }

    private void checkBluetoothSupport() {
        if (!bluetoothManager.isBluetoothSupported()) {
            connectButton.setEnabled(false);
            return;
        }

        if (!bluetoothManager.isBluetoothEnabled()) {
        }
    }

    public void handlePermissionDenied() {
        showAlert("Permissions Required", "Bluetooth permissions are required to discover and connect to devices.");
    }

    public void handleBluetoothDisabled() {
        showAlert("Bluetooth Required", "Bluetooth must be enabled to discover and connect to devices.");
    }

    private void showAlert(String title, String message) {
        new AlertDialog.Builder(this)
                .setTitle(title)
                .setMessage(message)
                .setPositiveButton("OK", null)
                .show();
    }

    private void showCoordinatePreview(String coordinates) {
        coordPreview.setText(coordinates);
        coordPreview.setVisibility(View.VISIBLE);
        coordPreview.postDelayed(() -> coordPreview.setVisibility(View.GONE), 2000);
    }

    private void appendMessage(String msg) {
        String oldText = messageBox.getText().toString();
        String newText = oldText.isEmpty() ? msg : oldText + "\n" + msg;
        messageBox.setText(newText);

        messageBox.post(() -> {
            int scrollAmount = messageBox.getLineCount() * messageBox.getLineHeight() - messageBox.getHeight();
            if (scrollAmount > 0) {
                messageBox.scrollTo(0, scrollAmount);
            }
        });
    }

    public void handleDeviceSelected(BluetoothDevice device) {
        Log.d(TAG, "Device selected: " + device.getAddress());
        bluetoothManager.connectToDevice(device);
    }

    public void handleDiscoveryCancelled() {
        Log.d(TAG, "Bluetooth discovery cancelled by user");
    }

    public void handleDiscoveryRefreshed() {
        Log.d(TAG, "Bluetooth discovery refreshed");
    }
}