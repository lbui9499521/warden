import logging
from cosmospy import CosmosClient, TxConfig, Transaction
from cosmospy.crypto.key import Signer

# Cấu hình logging
logging.basicConfig(filename="transactions.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# RPC của mạng Warden Buena Vista
rpc_endpoint = "https://rpc.buenavista.wardenprotocol.org/"

# Kết nối với mạng Warden Buena Vista
client = CosmosClient(rpc_endpoint)

# Đọc thông tin ví từ file wallets.txt
wallets = []
with open("wallets.txt", "r") as f:
    for line in f:
        address, private_key = line.strip().split(",")
        wallets.append({"address": address, "private_key": private_key, "balance": 0})

# Đọc thông tin giao dịch từ file transactions.txt
transactions = []
with open("transactions.txt", "r") as f:
    for line in f:
        to_address, amount = line.strip().split(",")
        transactions.append({"to": to_address, "amount": int(amount), "denom": "WARD"})  # Thay đổi denom thành WARD

# Cập nhật số dư ban đầu cho các ví
balances = {}
for wallet in wallets:
    try:
        account = client.get_account(wallet["address"])
        balances[wallet["address"]] = next((x["amount"] for x in account["coins"] if x["denom"] == "WARD"), 0) # Thay đổi denom thành WARD
    except Exception as e:
        logging.error(f"Lỗi khi lấy số dư của ví {wallet['address']}: {e}")

# Hàm kiểm tra số dư và gửi token
def send_tokens(from_address, private_key, to_address, amount, denom="WARD"):  # Đặt denom mặc định là WARD
    try:
        # Kiểm tra số dư
        if balances[from_address] < amount:
            logging.warning(f"Ví {from_address} không đủ số dư ({balances[from_address]} {denom})")
            return False

        # Tạo tin nhắn gửi token
        msg = client.bank.build_msg_send(
            from_address, to_address, amount=[{"amount": str(amount), "denom": denom}]
        )

        # Lấy thông tin tài khoản (để lấy số sequence mới nhất)
        account = client.get_account(from_address)

        # Chuẩn bị giao dịch
        tx_config = TxConfig(
            account_num=account["account_number"],
            sequence=account["sequence"],
            chain_id="buenavista-1",
            memo="",
            gas=100000,  # Gas limit mới
            fee= [{"amount": "2500", "denom": "uward"}]
        )

        # Ký và phát giao dịch
        tx = Transaction(client, msg, tx_config)
        private_key_bytes = bytes.fromhex(private_key)
        signer = Signer(private_key_bytes)
        tx.sign(signer)
        tx_result = client.broadcast_tx_sync(tx)
        logging.info(f"Transaction hash: {tx_result['txhash']}")

        # Cập nhật số dư sau khi gửi thành công
        balances[from_address] -= amount
        return True

    except Exception as e:
        logging.error(f"Lỗi khi gửi giao dịch từ {from_address}: {e}")
        return False

# Gửi các giao dịch
for tx in transactions:
    for wallet in wallets:
        if balances[wallet["address"]] >= tx["amount"]:
            if send_tokens(wallet["address"], wallet["private_key"], tx["to"], tx["amount"]):  # Không cần truyền denom vì đã mặc định
                break
    else:
        logging.error(f"Không đủ số dư để gửi giao dịch {tx}")
