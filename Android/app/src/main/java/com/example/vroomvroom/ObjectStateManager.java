// ObjectStateManager.java
package com.example.vroomvroom;

import android.content.Context;
import android.content.SharedPreferences;

public class ObjectStateManager {

    private static final String PREFS_NAME = "ObjectStates";
    private static final int MAX_STATES = 3;
    private static final int NUM_OBJECTS = 8;

    private Context context;
    private SharedPreferences prefs;

    public ObjectStateManager(Context context) {
        this.context = context;
        this.prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
    }

    // Save current state to a slot (1, 2, or 3)
    public boolean saveState(int slot, ObjectManager objectManager) {
        if (slot < 1 || slot > MAX_STATES) {
            return false;
        }

        SharedPreferences.Editor editor = prefs.edit();

        // Save all 8 objects
        for (int i = 1; i <= NUM_OBJECTS; i++) {
            String objectType = "OBJECT" + i;
            String prefix = "state_" + slot + "_obj_" + i + "_";

            editor.putInt(prefix + "x", objectManager.getObjectX(objectType));
            editor.putInt(prefix + "y", objectManager.getObjectY(objectType));
            editor.putString(prefix + "direction", objectManager.getObjectDirection(objectType));
            editor.putInt(prefix + "targetId", objectManager.getObjectTargetId(objectType));
            editor.putBoolean(prefix + "placed", objectManager.isObjectPlaced(objectType));
        }

        // Mark this slot as having data
        editor.putBoolean("state_" + slot + "_exists", true);

        return editor.commit();
    }

    // Load state from a slot
    public boolean loadState(int slot, ObjectManager objectManager) {
        if (slot < 1 || slot > MAX_STATES) {
            return false;
        }

        // Check if state exists
        if (!hasState(slot)) {
            return false;
        }

        // Load all objects
        for (int i = 1; i <= NUM_OBJECTS; i++) {
            String objectType = "OBJECT" + i;
            String prefix = "state_" + slot + "_obj_" + i + "_";

            int x = prefs.getInt(prefix + "x", -1);
            int y = prefs.getInt(prefix + "y", -1);
            String direction = prefs.getString(prefix + "direction", "N");
            int targetId = prefs.getInt(prefix + "targetId", i);

            objectManager.setObjectPosition(objectType, x, y);
            objectManager.setObjectDirection(objectType, direction);
            objectManager.setObjectTargetIdSameSize(objectType, targetId);
        }

        return true;
    }

    // Check if a slot has a saved state
    public boolean hasState(int slot) {
        if (slot < 1 || slot > MAX_STATES) {
            return false;
        }
        return prefs.getBoolean("state_" + slot + "_exists", false);
    }

    // Clear a specific state slot
    public void clearState(int slot) {
        if (slot < 1 || slot > MAX_STATES) {
            return;
        }

        SharedPreferences.Editor editor = prefs.edit();

        // Remove all object data for this slot
        for (int i = 1; i <= NUM_OBJECTS; i++) {
            String prefix = "state_" + slot + "_obj_" + i + "_";
            editor.remove(prefix + "x");
            editor.remove(prefix + "y");
            editor.remove(prefix + "direction");
            editor.remove(prefix + "targetId");
            editor.remove(prefix + "placed");
        }

        // Mark this slot as empty
        editor.remove("state_" + slot + "_exists");

        editor.apply();
    }

    // Clear all saved states
    public void clearAllStates() {
        SharedPreferences.Editor editor = prefs.edit();
        editor.clear();
        editor.apply();
    }
}