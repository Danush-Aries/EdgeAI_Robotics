#ifndef OPENCLAW_NVS_H
#define OPENCLAW_NVS_H

#include <<stdintstdint.h>
#include <<ststdbool.h>

typedef struct {
    float arm_pos_x;
    float arm_pos_y;
    float arm_pos_z;
    bool gripper_open;
    char device_id[32];
} robot_config_t;

bool nvs_save_config(robot_config_t* config);
bool nvs_load_config(robot_config_t* config);
void nvs_reset_defaults();

#endif
