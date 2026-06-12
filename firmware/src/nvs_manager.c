#include "nvs_manager.h"
#include <stdio.h>
#include <string.h>

// Mocking NVS for the purpose of the project structure as we are not on actual hardware
// In real ESP-IDF, this uses nvs_flash_init(), nvs_open(), etc.

static robot_config_t internal_storage;

bool nvs_save_config(robot_config_t* config) {
    printf("[NVS] Saving configuration to flash...\n");
    memcpy(&internal_storage, config, sizeof(robot_config_t));
    return true;
}

bool nvs_load_config(robot_config_t* config) {
    printf("[NVS] Loading configuration from flash...\n");
    memcpy(config, &internal_storage, sizeof(robot_config_t));
    return true;
}

void nvs_reset_defaults() {
    printf("[NVS] Resetting to factory defaults...\n");
    internal_storage.arm_pos_x = 0.0f;
    internal_storage.arm_pos_y = 0.0f;
    internal_storage.arm_pos_z = 0.0f;
    internal_storage.gripper_open = true;
    strcpy(internal_storage.device_id, "OPENCLAW-001");
}
