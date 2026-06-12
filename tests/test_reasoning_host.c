/*
 * test_reasoning_host.c
 * ---------------------
 * Host-side unit tests for the firmware reasoning module.
 * Compiles and runs on any POSIX system – no ESP32 toolchain required.
 *
 * Build & run:
 *   cd tests
 *   gcc -I../firmware/include -o test_reasoning \
 *       test_reasoning_host.c ../firmware/src/reasoning.c \
 *       ../firmware/src/nvs_manager.c && ./test_reasoning
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <assert.h>

#include "reasoning.h"
#include "nvs_manager.h"

/* ------------------------------------------------------------------ */
/* Tiny test harness                                                   */
/* ------------------------------------------------------------------ */
static int g_pass = 0;
static int g_fail = 0;

#define CHECK(expr) \
    do { \
        if (expr) { \
            printf("  PASS  %s\n", #expr); \
            g_pass++; \
        } else { \
            printf("  FAIL  %s  (line %d)\n", #expr, __LINE__); \
            g_fail++; \
        } \
    } while (0)

/* ------------------------------------------------------------------ */
/* Tests: process_reasoning_step                                       */
/* ------------------------------------------------------------------ */

static void test_parse_move_action(void) {
    printf("\n[test_parse_move_action]\n");
    react_step_t step = {0};
    const char* input = "Thought: Arm must move to target position. | Action: MOVE";
    CHECK(process_reasoning_step(input, &step) == true);
    CHECK(strcmp(step.action.params, "MOVE") == 0);
    CHECK(step.action.id == TOOL_MOVE_ARM);
    CHECK(strstr(step.thought, "Arm must move") != NULL);
}

static void test_parse_grip_action(void) {
    printf("\n[test_parse_grip_action]\n");
    react_step_t step = {0};
    const char* input = "Thought: Closing the gripper to secure the object. | Action: GRIP";
    CHECK(process_reasoning_step(input, &step) == true);
    CHECK(strcmp(step.action.params, "GRIP") == 0);
    CHECK(step.action.id == TOOL_GRIPPER);
}

static void test_parse_sensor_action(void) {
    printf("\n[test_parse_sensor_action]\n");
    react_step_t step = {0};
    const char* input = "Thought: Reading environment sensors. | Action: SENSOR";
    CHECK(process_reasoning_step(input, &step) == true);
    CHECK(step.action.id == TOOL_READ_SENSORS);
}

static void test_parse_unknown_action(void) {
    printf("\n[test_parse_unknown_action]\n");
    react_step_t step = {0};
    const char* input = "Thought: Doing something weird. | Action: DANCE";
    CHECK(process_reasoning_step(input, &step) == true);
    CHECK(step.action.id == TOOL_UNKNOWN);
}

static void test_missing_action_field(void) {
    printf("\n[test_missing_action_field]\n");
    react_step_t step = {0};
    const char* input = "Thought: Only thought, no action.";
    CHECK(process_reasoning_step(input, &step) == false);
}

static void test_missing_thought_field(void) {
    printf("\n[test_missing_thought_field]\n");
    react_step_t step = {0};
    const char* input = "Action: MOVE";
    CHECK(process_reasoning_step(input, &step) == false);
}

static void test_empty_input(void) {
    printf("\n[test_empty_input]\n");
    react_step_t step = {0};
    CHECK(process_reasoning_step("", &step) == false);
}

static void test_thought_buffer_not_overflowed(void) {
    /* Feed a thought that is longer than the 255-char buffer limit */
    printf("\n[test_thought_buffer_not_overflowed]\n");
    char long_thought[512];
    memset(long_thought, 'A', sizeof(long_thought) - 1);
    long_thought[sizeof(long_thought) - 1] = '\0';

    char input[600];
    snprintf(input, sizeof(input), "Thought: %s | Action: MOVE", long_thought);

    react_step_t step = {0};
    int result = process_reasoning_step(input, &step);
    /* Must not crash; thought must be null-terminated within bounds */
    CHECK(result == true || result == false); /* just ensure no crash */
    CHECK(strlen(step.thought) < sizeof(step.thought));
    CHECK(step.thought[sizeof(step.thought) - 1] == '\0');
}

/* ------------------------------------------------------------------ */
/* Tests: NVS manager                                                  */
/* ------------------------------------------------------------------ */

static void test_nvs_reset_and_load(void) {
    printf("\n[test_nvs_reset_and_load]\n");
    nvs_reset_defaults();
    robot_config_t cfg = {0};
    CHECK(nvs_load_config(&cfg) == true);
    CHECK(strcmp(cfg.device_id, "OPENCLAW-001") == 0);
    CHECK(cfg.arm_pos_x == 0.0f);
    CHECK(cfg.arm_pos_y == 0.0f);
    CHECK(cfg.arm_pos_z == 0.0f);
    CHECK(cfg.gripper_open == true);
}

static void test_nvs_save_and_reload(void) {
    printf("\n[test_nvs_save_and_reload]\n");
    robot_config_t original = {
        .arm_pos_x = 10.5f,
        .arm_pos_y = 20.0f,
        .arm_pos_z = 5.25f,
        .gripper_open = false,
        .device_id = "TEST-UNIT",
    };
    CHECK(nvs_save_config(&original) == true);

    robot_config_t loaded = {0};
    CHECK(nvs_load_config(&loaded) == true);
    CHECK(loaded.arm_pos_x == 10.5f);
    CHECK(loaded.arm_pos_y == 20.0f);
    CHECK(loaded.arm_pos_z == 5.25f);
    CHECK(loaded.gripper_open == false);
    CHECK(strcmp(loaded.device_id, "TEST-UNIT") == 0);
}

/* ------------------------------------------------------------------ */
/* Main                                                                */
/* ------------------------------------------------------------------ */

int main(void) {
    printf("=== OpenClaw Firmware Unit Tests (host) ===\n");

    reasoning_init();

    test_parse_move_action();
    test_parse_grip_action();
    test_parse_sensor_action();
    test_parse_unknown_action();
    test_missing_action_field();
    test_missing_thought_field();
    test_empty_input();
    test_thought_buffer_not_overflowed();
    test_nvs_reset_and_load();
    test_nvs_save_and_reload();

    printf("\n=== Results: %d passed, %d failed ===\n", g_pass, g_fail);
    return (g_fail == 0) ? 0 : 1;
}
