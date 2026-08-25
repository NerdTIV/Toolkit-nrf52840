/* SPDX-License-Identifier: Apache-2.0 */

#include <zephyr/kernel.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(periph, LOG_LEVEL_INF);

#define NUS_SVC BT_UUID_128_ENCODE(0x6e400001, 0xb5a3, 0xf393, 0xe0a9, 0xe50e24dcca9e)
#define NUS_RX  BT_UUID_128_ENCODE(0x6e400002, 0xb5a3, 0xf393, 0xe0a9, 0xe50e24dcca9e)
#define NUS_TX  BT_UUID_128_ENCODE(0x6e400003, 0xb5a3, 0xf393, 0xe0a9, 0xe50e24dcca9e)

static struct bt_uuid_128 nus_svc = BT_UUID_INIT_128(NUS_SVC);
static struct bt_uuid_128 nus_rx  = BT_UUID_INIT_128(NUS_RX);
static struct bt_uuid_128 nus_tx  = BT_UUID_INIT_128(NUS_TX);

static uint8_t tx_val[50] = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMN";

static ssize_t read_tx(struct bt_conn *conn, const struct bt_gatt_attr *attr,
		       void *buf, uint16_t len, uint16_t offset)
{

	return bt_gatt_attr_read(conn, attr, buf, len, offset,
				 tx_val, sizeof(tx_val));
}

static ssize_t write_rx(struct bt_conn *conn, const struct bt_gatt_attr *attr,
			const void *buf, uint16_t len, uint16_t offset,
			uint8_t flags)
{
	LOG_INF("RX %u bytes", len);
	return len;
}

static void ccc_changed(const struct bt_gatt_attr *attr, uint16_t value)
{
	if (value == BT_GATT_CCC_NOTIFY) {
		LOG_INF("notifications on");
	} else {
		LOG_INF("notifications off");
	}
}

BT_GATT_SERVICE_DEFINE(nus,
	BT_GATT_PRIMARY_SERVICE(&nus_svc),
	BT_GATT_CHARACTERISTIC(&nus_tx.uuid,
		BT_GATT_CHRC_READ | BT_GATT_CHRC_NOTIFY,
		BT_GATT_PERM_READ, read_tx, NULL, NULL),
	BT_GATT_CCC(ccc_changed, BT_GATT_PERM_READ | BT_GATT_PERM_WRITE),
	BT_GATT_CHARACTERISTIC(&nus_rx.uuid,
		BT_GATT_CHRC_WRITE | BT_GATT_CHRC_WRITE_WITHOUT_RESP,
		BT_GATT_PERM_WRITE, NULL, write_rx, NULL),
);

static const struct bt_data ad[] = {
	BT_DATA_BYTES(BT_DATA_FLAGS, BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR),
	BT_DATA(BT_DATA_NAME_COMPLETE, "ZephyrPeriph", 12),
};

static void connected(struct bt_conn *conn, uint8_t err)
{
	LOG_INF("central connected (err %u)", err);
}

static void disconnected(struct bt_conn *conn, uint8_t reason)
{
	LOG_INF("disconnected (reason 0x%02x)", reason);
}

BT_CONN_CB_DEFINE(conn_cb) = {
	.connected = connected,
	.disconnected = disconnected,
};

int main(void)
{
	int err;

	err = bt_enable(NULL);
	if (err) {
		LOG_ERR("bt_enable failed : %d", err);
		return 0;
	}

	err = bt_le_adv_start(BT_LE_ADV_CONN_FAST_1, ad, ARRAY_SIZE(ad), NULL, 0);
	if (err) {
		LOG_ERR("adv start failed : %d", err);
		return 0;
	}

	LOG_INF("peripheral up, advertising 'ZephyrPeriph'");
	return 0;
}
