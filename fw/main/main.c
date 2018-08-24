/* servo motor control example

   This example code is in the Public Domain (or CC0 licensed, at your option.)

   Unless required by applicable law or agreed to in writing, this
   software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
   CONDITIONS OF ANY KIND, either express or implied.
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <sys/time.h>

#include "esp_attr.h"
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "freertos/task.h"

#include "driver/mcpwm.h"
#include "soc/mcpwm_reg.h"
#include "soc/mcpwm_struct.h"

#include "esp_bt.h"
#include "esp_bt_defs.h"
#include "esp_bt_main.h"
#include "esp_gap_ble_api.h"
#include "esp_gatt_common_api.h"
#include "esp_gatts_api.h"
#include "esp_log.h"
#include "esp_system.h"
#include "nvs_flash.h"

#include "sdkconfig.h"

#define GATTS_SERVICE_UUID_MOTOR 0x0420
#define GATTS_CHAR_UUID_MOTOR_CTRL 0x1337
#define GATTS_NUM_HANDLES 8

#define DEVICE_NAME "Egg."
#define GATTS_CHAR_VAL_LEN_MAX 0xFF

#define CHARACTERISTIC_MOTOR_CTRL_ID 0
#define CHARACTERISTIC_MOTOR_NAME "Servo Angle"

#define SERVO_MIN_PULSEWIDTH 400
#define SERVO_MAX_PULSEWIDTH 2400
#define SERVO_MAX_DEGREE 180
#define SECONDS_PER_SWEEP 5

bool connected = false;

static void set_angle(uint32_t degree_of_rotation) {
  uint32_t cal_pulsewidth =
      (SERVO_MIN_PULSEWIDTH +
       (((SERVO_MAX_PULSEWIDTH - SERVO_MIN_PULSEWIDTH) * (degree_of_rotation)) /
        (SERVO_MAX_DEGREE)));
  mcpwm_set_duty_in_us(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_A,
                       cal_pulsewidth);
}

esp_attr_value_t gatts_attr_val = {
    .attr_max_len = GATTS_CHAR_VAL_LEN_MAX,
    .attr_len = sizeof(CHARACTERISTIC_MOTOR_NAME),
    .attr_value = (uint8_t *)(CHARACTERISTIC_MOTOR_NAME),
};

static uint8_t service_uuid128[32] = {
    0xfb, 0x34, 0x9b, 0x5f, 0x80, 0x00, 0x00, 0x80,
    0x00, 0x10, 0x00, 0x00, 0xAB, 0xCD, 0x00, 0x00,
};

static esp_ble_adv_data_t adv_data = {
    .set_scan_rsp = false,
    .include_name = true,
    .include_txpower = true,
    .min_interval = 0x20,
    .max_interval = 0x40,
    .appearance = 0x00,
    .manufacturer_len = 0,
    .p_manufacturer_data = NULL,
    .service_data_len = 0,
    .p_service_data = NULL,
    .service_uuid_len = 16,
    .p_service_uuid = service_uuid128,
    .flag = (ESP_BLE_ADV_FLAG_GEN_DISC | ESP_BLE_ADV_FLAG_BREDR_NOT_SPT),
};

esp_ble_adv_params_t adv_params = {
    .adv_int_min = 0x20,
    .adv_int_max = 0x40,
    .adv_type = ADV_TYPE_IND,
    .own_addr_type = BLE_ADDR_TYPE_PUBLIC,
    .channel_map = ADV_CHNL_ALL,
    .adv_filter_policy = ADV_FILTER_ALLOW_SCAN_ANY_CON_ANY,
};

uint16_t app_id, conn_id, service_handle, gatts_if = ESP_GATT_IF_NONE;
esp_gatt_srvc_id_t service_id = {
    .is_primary = true,
    .id.inst_id = 0x00,
    .id.uuid.len = ESP_UUID_LEN_16,
    .id.uuid.uuid.uuid16 = GATTS_SERVICE_UUID_MOTOR,
};

esp_bt_uuid_t char_uuid = {
    .len = ESP_UUID_LEN_16,
    .uuid.uuid16 = GATTS_CHAR_UUID_MOTOR_CTRL,
};

esp_bt_uuid_t descr_uuid;
uint16_t char_handle;
uint16_t descr_handle;

static void gap_event_handler(esp_gap_ble_cb_event_t event,
                              esp_ble_gap_cb_param_t *param) {
  switch (event) {
  case ESP_GAP_BLE_ADV_DATA_SET_COMPLETE_EVT:
  case ESP_GAP_BLE_ADV_DATA_RAW_SET_COMPLETE_EVT:
  case ESP_GAP_BLE_SCAN_RSP_DATA_RAW_SET_COMPLETE_EVT:
    esp_ble_gap_start_advertising(&adv_params);
    break;
  case ESP_GAP_BLE_ADV_START_COMPLETE_EVT:
    // advertising start complete event to indicate advertising start
    // successfully or failed
    if (param->adv_start_cmpl.status != ESP_BT_STATUS_SUCCESS) {
      printf("\nAdvertising start failed\n");
    }
    break;
  case ESP_GAP_BLE_ADV_STOP_COMPLETE_EVT:
    if (param->adv_stop_cmpl.status != ESP_BT_STATUS_SUCCESS) {
      printf("\nAdvertising stop failed\n");
    } else {
      printf("\nStop adv successfully\n");
    }
    break;
  default:
    break;
  }
}

void process_write_event_env(esp_gatt_if_t gatts_if,
                             esp_ble_gatts_cb_param_t *param) {
  if (char_handle == param->write.handle) {
    if (param->write.len == 1) {
      if (((unsigned char *)param->write.value)[0] > SERVO_MAX_DEGREE) {
        set_angle(SERVO_MAX_DEGREE);
      } else {
        set_angle(((unsigned char *)param->write.value)[0]);
      }
    }
  }
  /* send response if any */
  if (param->write.need_rsp) {
    printf("respond");
    esp_err_t response_err =
        esp_ble_gatts_send_response(gatts_if, param->write.conn_id,
                                    param->write.trans_id, ESP_GATT_OK, NULL);
    if (response_err != ESP_OK) {
      printf("\nSend response error\n");
    }
  }
}

static void gatts_profile_event_handler(esp_gatts_cb_event_t event,
                                        esp_gatt_if_t gatts_if,
                                        esp_ble_gatts_cb_param_t *param) {
  switch (event) {
    // When register application id, the event comes
  case ESP_GATTS_REG_EVT: {
    printf("\nREGISTER_APP_EVT, status %d, app_id %d\n", param->reg.status,
           param->reg.app_id);

    service_id.is_primary = true;
    service_id.id.inst_id = 0x00;
    service_id.id.uuid.len = ESP_UUID_LEN_16;
    service_id.id.uuid.uuid.uuid16 = GATTS_SERVICE_UUID_MOTOR;

    esp_err_t set_dev_name_ret = esp_ble_gap_set_device_name(DEVICE_NAME);
    if (set_dev_name_ret) {
      printf("set device name failed, error code = %x", set_dev_name_ret);
    }

    // config adv data
    esp_err_t ret = esp_ble_gap_config_adv_data(&adv_data);
    if (ret) {
      printf("config adv data failed, error code = %x", ret);
    }

    // config scan response data
    ret = esp_ble_gap_config_adv_data(&adv_data);
    if (ret) {
      printf("config scan response data failed, error code = %x", ret);
    }

    esp_ble_gatts_create_service(gatts_if, &service_id, GATTS_NUM_HANDLES);
    break;
  }
  case ESP_GATTS_WRITE_EVT: {
    printf("\nESP_GATTS_WRITE_EVT\n");
    process_write_event_env(gatts_if, param);
    break;
  }
  case ESP_GATTS_CREATE_EVT: {
    printf("\nstatus %d, service_handle %x, service id %x\n",
                  param->create.status, param->create.service_handle,
                  param->create.service_id.id.uuid.uuid.uuid16);

    service_handle = param->create.service_handle;

    esp_ble_gatts_add_char(service_handle, &char_uuid, ESP_GATT_PERM_WRITE, ESP_GATT_CHAR_PROP_BIT_WRITE,
                           &gatts_attr_val, NULL);

    esp_ble_gatts_start_service(service_handle);
    break;
  }
    // When add characteristic complete, the event comes
  case ESP_GATTS_ADD_CHAR_EVT: {
    printf("\nADD_CHAR_EVT, status %d,  attr_handle %x, service_handle "
                  "%x, char uuid %x\n",
                  param->add_char.status, param->add_char.attr_handle,
                  param->add_char.service_handle,
                  param->add_char.char_uuid.uuid.uuid16);
    /* store characteristic handles for later usage */
    if (param->add_char.char_uuid.uuid.uuid16 == GATTS_CHAR_UUID_MOTOR_CTRL) {
      char_handle = param->add_char.attr_handle;
    }
    break;
  }
  case ESP_GATTS_DISCONNECT_EVT: {
    connected = false;
    esp_ble_gap_start_advertising(&adv_params);
    break;
  }
  case ESP_GATTS_CONNECT_EVT: {
    printf("\nESP_GATTS_CONNECT_EVT\n");
    connected = true;
    esp_ble_conn_update_params_t conn_params = {0};
    memcpy(conn_params.bda, param->connect.remote_bda, sizeof(esp_bd_addr_t));
    /* For the IOS system, please reference the apple official documents about
     * the ble connection parameters restrictions. */
    conn_params.latency = 0;
    conn_params.max_int = 0x50; // max_int = 0x50*1.25ms = 100ms
    conn_params.min_int = 0x30; // min_int = 0x30*1.25ms = 60ms
    conn_params.timeout = 1000; // timeout = 1000*10ms = 10000ms
    conn_id = param->connect.conn_id;
    // start sent the update connection parameters to the peer device.
    esp_ble_gap_update_conn_params(&conn_params);
    break;
  }
  default:
    break;
  }
}

static void gatts_event_handler(esp_gatts_cb_event_t event,
                                esp_gatt_if_t _gatts_if,
                                esp_ble_gatts_cb_param_t *param) {
  /* If event is register event, store the gatts_if for the profile */
  if (event == ESP_GATTS_REG_EVT) {
    if (param->reg.status == ESP_GATT_OK) {
      gatts_if = _gatts_if;
    } else {
      printf("\nReg app failed, app_id %04x, status %d\n", param->reg.app_id,
             param->reg.status);
      return;
    }
  }

  if (_gatts_if == ESP_GATT_IF_NONE || _gatts_if == gatts_if) {
    gatts_profile_event_handler(event, _gatts_if, param);
  }
}

void setup_bluetooth() {
  esp_err_t ret;

  // Initialize NVS.
  ret = nvs_flash_init();
  if (ret == ESP_ERR_NVS_NO_FREE_PAGES ||
      ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
    ESP_ERROR_CHECK(nvs_flash_erase());
    ret = nvs_flash_init();
  }
  ESP_ERROR_CHECK(ret);

  ESP_ERROR_CHECK(esp_bt_controller_mem_release(ESP_BT_MODE_CLASSIC_BT));

  esp_bt_controller_config_t bt_cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
  ret = esp_bt_controller_init(&bt_cfg);
  if (ret) {
    printf("initialize controller failed\n");
    return;
  }

  ret = esp_bt_controller_enable(ESP_BT_MODE_BLE);
  if (ret) {
    printf("enable controller failed\n");
    return;
  }

  ret = esp_bluedroid_init();
  if (ret) {
    printf("init bluetooth failed\n");
    return;
  }

  ret = esp_bluedroid_enable();
  if (ret) {
    printf("enable bluetooth failed\n");
    return;
  }

  ret = esp_ble_gatts_register_callback(gatts_event_handler);
  if (ret) {
    printf("gatts register error, error code = %x", ret);
    return;
  }

  ret = esp_ble_gap_register_callback(gap_event_handler);
  if (ret) {
    printf("gap register error, error code = %x", ret);
    return;
  }

  ret = esp_ble_gap_set_device_name(DEVICE_NAME);
  if (ret) {
    printf("set device name failed\n");
    return;
  }

  ret = esp_ble_gap_config_adv_data(&adv_data);
  if (ret) {
    printf("set advertising data failed");
    return;
  }

  ret = esp_ble_gatts_app_register(CHARACTERISTIC_MOTOR_CTRL_ID);
  if (ret) {
    printf("gatts app register error, error code = %x", ret);
    return;
  }

  esp_err_t local_mtu_ret = esp_ble_gatt_set_local_mtu(500);
  if (local_mtu_ret) {
    printf("set local MTU failed, error code = %x", local_mtu_ret);
  }

  return;
}

void servo_idle() {
  struct timeval tv;
  while (true) {
    while (!connected) {
      gettimeofday(&tv, NULL);
      double time = ((tv.tv_sec % (SECONDS_PER_SWEEP * 2)) +
                     ((double)tv.tv_usec / 1000000));
      if (time > SECONDS_PER_SWEEP) {
        time = (SECONDS_PER_SWEEP * 2) - time;
      }
      time /= SECONDS_PER_SWEEP;
      set_angle(time * SERVO_MAX_DEGREE);
    }
    while (connected) {
      vTaskDelay(100);
    }
  }
}

static void setup_servo() {
  mcpwm_gpio_init(MCPWM_UNIT_0, MCPWM0A, 32);

  mcpwm_config_t pwm_config = {
      .frequency = 50,
      .cmpr_a = 0,
      .cmpr_b = 0,
      .counter_mode = MCPWM_UP_COUNTER,
      .duty_mode = MCPWM_DUTY_MODE_0,
  };
  mcpwm_init(MCPWM_UNIT_0, MCPWM_TIMER_0, &pwm_config);

  set_angle(90);
  xTaskCreate(servo_idle, "servo_idle", 4096, NULL, 5, NULL);
}

void app_main() {
  setup_bluetooth();
  setup_servo();
}
