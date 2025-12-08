import time
import smtplib
import json
import os
import threading
from flask import Flask
from email.mime.text import MIMEText
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ================= FAKE WEB SERVER FOR RENDER =================
# This allows the bot to "listen" on a port so Render keeps it alive.
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Multisig Bot is running correctly!"

def run_web_server():
    # Render sets the PORT env var automatically (defaults to 10000)
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
# ==============================================================

# ================= CONFIGURATION =================

# 1. AUTHENTICATION & KEYS
PRIVATE_KEY = os.getenv("BOT_PRIVATE_KEY")
EMAIL_PASS = os.getenv("EMAIL_APP_PASSWORD")
SENDER_EMAIL = os.getenv("EMAIL_USER")

# Parse recipients safely
recipients_str = os.getenv("RECIPIENTS")
if recipients_str:
    RECIPIENT_EMAILS = recipients_str.split(",")
else:
    RECIPIENT_EMAILS = []

# 2. TARGET CHAINS
CHAINS = [
    {
        "name": "Celo",
        "rpc": "https://forno.celo.org",
        "contract": "0x91EaAcBa3c58EA499e229e703cbA3e6eBb52607E", 
        "explorer": "https://celoscan.io/tx/"
    },
    {
        "name": "Optimism",
        "rpc": "https://mainnet.optimism.io",
        "contract": "0x91EaAcBa3c58EA499e229e703cbA3e6eBb52607E",
        "explorer": "https://optimistic.etherscan.io/tx/"
    },
    {
        "name": "Lisk",
        "rpc": "https://rpc.api.lisk.com",
        "contract": "0x91EaAcBa3c58EA499e229e703cbA3e6eBb52607E",
        "explorer": "https://blockscout.lisk.com/tx/"
    },
    {
        "name": "Arbitrum",
        "rpc": "https://arb1.arbitrum.io/rpc",
        "contract": "0x91EaAcBa3c58EA499e229e703cbA3e6eBb52607E",
        "explorer": "https://arbiscan.io/tx/"
    },
    {
        "name": "Base",
        "rpc": "https://mainnet.base.org",
        "contract": "0x91EaAcBa3c58EA499e229e703cbA3e6eBb52607E",
        "explorer": "https://basescan.org/tx/"
    }
]

# 3. LIST OF EVENTS TO WATCH
WATCHED_EVENTS = [
    "TransactionSubmitted",
    "TransactionConfirmed",
    "TransactionExecuted",
    "TransactionRevoked",
    "OwnerAdded",
    "OwnerRemoved",
    "ContractPaused",
    "ContractUnpaused"
]

# 4. ABI (Full ABI required)
CONTRACT_ABI = json.loads('''[
    {"inputs":[{"internalType":"address","name":"_companyWallet","type":"address"},{"internalType":"address","name":"_ceo","type":"address"},{"internalType":"string","name":"_ceoName","type":"string"},{"internalType":"address","name":"_cto","type":"address"},{"internalType":"string","name":"_ctoName","type":"string"},{"internalType":"address","name":"_cfo","type":"address"},{"internalType":"string","name":"_cfoName","type":"string"}],"stateMutability":"nonpayable","type":"constructor"},
    {"anonymous":false,"inputs":[],"name":"ContractPaused","type":"event"},
    {"anonymous":false,"inputs":[],"name":"ContractUnpaused","type":"event"},
    {"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"newPeriod","type":"uint256"}],"name":"ExpiryPeriodChanged","type":"event"},
    {"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"newMinOwners","type":"uint256"}],"name":"MinOwnersChanged","type":"event"},
    {"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":false,"internalType":"string","name":"name","type":"string"},{"indexed":false,"internalType":"uint256","name":"percentage","type":"uint256"}],"name":"OwnerAdded","type":"event"},
    {"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"}],"name":"OwnerRemoved","type":"event"},
    {"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"newPercentage","type":"uint256"}],"name":"RequiredPercentageChanged","type":"event"},
    {"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"newPeriod","type":"uint256"}],"name":"TimelockPeriodChanged","type":"event"},
    {"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint256","name":"transactionId","type":"uint256"},{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":false,"internalType":"uint256","name":"percentage","type":"uint256"}],"name":"TransactionConfirmed","type":"event"},
    {"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint256","name":"transactionId","type":"uint256"}],"name":"TransactionExecuted","type":"event"},
    {"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint256","name":"transactionId","type":"uint256"},{"indexed":true,"internalType":"address","name":"owner","type":"address"}],"name":"TransactionRevoked","type":"event"},
    {"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint256","name":"transactionId","type":"uint256"},{"indexed":true,"internalType":"address","name":"initiator","type":"address"},{"indexed":true,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"},{"indexed":false,"internalType":"bool","name":"isTokenTransfer","type":"bool"},{"indexed":false,"internalType":"address","name":"tokenAddress","type":"address"},{"indexed":false,"internalType":"bytes","name":"data","type":"bytes"}],"name":"TransactionSubmitted","type":"event"},
    {"inputs":[{"internalType":"address","name":"newOwner","type":"address"},{"internalType":"string","name":"name","type":"string"},{"internalType":"uint256","name":"percentage","type":"uint256"}],"name":"addOwnerInternal","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"newPercentage","type":"uint256"}],"name":"changeRequiredPercentageInternal","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[],"name":"companyWallet","outputs":[{"internalType":"contract ICompanyWallet","name":"","type":"address"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"transactionId","type":"uint256"}],"name":"confirmTransaction","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256[]","name":"transactionIds","type":"uint256[]"}],"name":"confirmTransactionsBatch","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[],"name":"deployer","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"transactionId","type":"uint256"}],"name":"executeTransactionManual","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[],"name":"expiryPeriod","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"getOwnerCount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"getOwners","outputs":[{"internalType":"address[]","name":"addresses","type":"address[]"},{"internalType":"string[]","name":"names","type":"string[]"},{"internalType":"uint256[]","name":"percentages","type":"uint256[]"},{"internalType":"bool[]","name":"removables","type":"bool[]"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"getPoolPercentage","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"transactionId","type":"uint256"}],"name":"getTransaction","outputs":[{"internalType":"address","name":"initiator","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"},{"internalType":"bytes","name":"data","type":"bytes"},{"internalType":"bool","name":"isTokenTransfer","type":"bool"},{"internalType":"address","name":"tokenAddress","type":"address"},{"internalType":"bool","name":"executed","type":"bool"},{"internalType":"uint256","name":"confirmationCount","type":"uint256"},{"internalType":"uint256","name":"timestamp","type":"uint256"},{"internalType":"uint256","name":"timelockEnd","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"getTransactionCount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"transactionId","type":"uint256"},{"internalType":"address","name":"owner","type":"address"}],"name":"hasConfirmed","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"transactionId","type":"uint256"}],"name":"isConfirmed","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"minOwners","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"ownerAddresses","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"owners","outputs":[{"internalType":"address","name":"ownerAddress","type":"address"},{"internalType":"string","name":"name","type":"string"},{"internalType":"uint256","name":"percentage","type":"uint256"},{"internalType":"bool","name":"exists","type":"bool"},{"internalType":"bool","name":"isRemovable","type":"bool"},{"internalType":"uint256","name":"index","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"pause","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[],"name":"paused","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"poolPercentage","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"ownerToRemove","type":"address"}],"name":"removeOwnerInternal","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[],"name":"requiredPercentage","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"transactionId","type":"uint256"}],"name":"revokeConfirmation","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"newOwner","type":"address"},{"internalType":"string","name":"name","type":"string"},{"internalType":"uint256","name":"percentage","type":"uint256"}],"name":"submitAddOwner","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"newPercentage","type":"uint256"}],"name":"submitChangeRequiredPercentage","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"ownerToRemove","type":"address"}],"name":"submitRemoveOwner","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"},{"internalType":"bool","name":"isTokenTransfer","type":"bool"},{"internalType":"address","name":"tokenAddress","type":"address"},{"internalType":"bytes","name":"data","type":"bytes"}],"name":"submitTransaction","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[],"name":"test","outputs":[],"stateMutability":"pure","type":"function"},
    {"inputs":[],"name":"timelockPeriod","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"transactions","outputs":[{"internalType":"address","name":"initiator","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"},{"internalType":"bytes","name":"data","type":"bytes"},{"internalType":"bool","name":"isTokenTransfer","type":"bool"},{"internalType":"address","name":"tokenAddress","type":"address"},{"internalType":"bool","name":"executed","type":"bool"},{"internalType":"uint256","name":"confirmationCount","type":"uint256"},{"internalType":"uint256","name":"timestamp","type":"uint256"},{"internalType":"uint256","name":"timelockEnd","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"unpause","outputs":[],"stateMutability":"nonpayable","type":"function"}
]''')

# ================= CORE LOGIC =================

def send_alert(chain_name, event_name, event_args, tx_hash):
    """
    Sends an email with detailed content about any event.
    """
    if not RECIPIENT_EMAILS:
        print("⚠️ No recipients found in .env")
        return

    # 1. Format the arguments into a readable list
    # event_args is a dictionary (AttributeDict), so we loop through it
    details_str = ""
    for key, value in event_args.items():
        # Clean up bytes data for readability
        if isinstance(value, bytes):
            value = value.hex()
        details_str += f"- {key}: {value}\n"

    # 2. Construct the Email Body
    body = f"""
    🔔 Multisig Update: {event_name}
    ========================================
    Chain: {chain_name}
    Event: {event_name}
    
    Details:
    {details_str}
    
    ----------------------------------------
    View Transaction:
    {tx_hash}
    """

    # 3. Send Email
    msg = MIMEText(body)
    msg["Subject"] = f"[{chain_name}] {event_name} Detected"
    msg["From"] = SENDER_EMAIL
    msg["To"] = ", ".join(RECIPIENT_EMAILS)

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, EMAIL_PASS)
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAILS, msg.as_string())
        server.quit()
        print(f"📧 Email sent for {event_name}")
    except Exception as e:
        print(f"❌ Email Failed: {e}")

def attempt_execution(w3, contract, chain_name, tx_id):
    """Checks requirements and executes if ready."""
    try:
        # Fetch detailed tx data
        tx_data = contract.functions.getTransaction(tx_id).call()
        is_executed = tx_data[6]
        timelock_end = tx_data[9]
        
        # 1. Stop if already executed
        if is_executed:
            return

        # 2. Check if confirmed enough
        is_confirmed = contract.functions.isConfirmed(tx_id).call()
        if not is_confirmed:
            return # Waiting for more signatures
        
        # 3. Check Timelock
        current_time = w3.eth.get_block('latest')['timestamp']
        if timelock_end > 0 and current_time >= timelock_end:
            print(f"⚡ Executing Tx #{tx_id} on {chain_name}...")
            
            # Build Transaction
            account = w3.eth.account.from_key(PRIVATE_KEY)
            nonce = w3.eth.get_transaction_count(account.address)
            
            tx_params = {
                'from': account.address,
                'nonce': nonce,
            }

            if chain_name == "Celo":
                tx_params['gasPrice'] = w3.eth.generate_gas_price()
            else:
                tx_params['gasPrice'] = w3.eth.gas_price

            build_tx = contract.functions.executeTransactionManual(tx_id).build_transaction(tx_params)
            
            # Sign & Send
            signed_tx = w3.eth.account.sign_transaction(build_tx, PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            print(f"✅ EXECUTION SENT! Hash: {w3.to_hex(tx_hash)}")
            
    except Exception as e:
        if "revert" not in str(e).lower():
            print(f"⚠️ Execution check failed for {tx_id} on {chain_name}: {e}")

def main():
    print("🤖 Bot Started. Watching ALL Events & Executing...")
    
    state = {} 

    while True:
        for chain in CHAINS:
            try:
                # Initialize Web3
                w3 = Web3(Web3.HTTPProvider(chain["rpc"]))
                if not w3.is_connected():
                    print(f"⚠️ Failed to connect to {chain['name']}")
                    continue

                contract = w3.eth.contract(address=chain["contract"], abi=CONTRACT_ABI)
                
                # Setup State
                if chain["name"] not in state:
                    state[chain["name"]] = w3.eth.block_number
                
                last_block = state[chain["name"]]
                current_block = w3.eth.block_number
                
                if current_block > last_block:
                    print(f"Scanning {chain['name']} blocks {last_block} to {current_block}...")
                    
                    # === LOOP THROUGH ALL WATCHED EVENTS ===
                    for event_name in WATCHED_EVENTS:
                        try:
                            # Dynamically get the event object by name
                            event_obj = getattr(contract.events, event_name)
                            
                            # Get logs
                            events = event_obj.get_logs(from_block=last_block)
                            
                            for event in events:
                                # Get specific details (args)
                                args = event["args"]
                                tx_hash = event["transactionHash"].hex()
                                
                                print(f"🔥 {event_name} detected on {chain['name']}")
                                
                                # Send Rich Email
                                send_alert(chain["name"], event_name, args, chain['explorer'] + tx_hash)
                        
                        except Exception as ev_err:
                            # Some events might not exist in older ABI versions or might fail
                            print(f"Skipping event {event_name}: {ev_err}")

                    # Update state only after checking all events
                    state[chain["name"]] = current_block

                # === AUTO EXECUTION CHECK ===
                # Check last 5 transactions
                total_count = contract.functions.getTransactionCount().call()
                start_check = max(0, total_count - 5)
                for i in range(start_check, total_count):
                    attempt_execution(w3, contract, chain["name"], i)

            except Exception as e:
                print(f"Error on {chain['name']}: {e}")

        time.sleep(12)

if __name__ == "__main__":
    # 1. Start the Fake Web Server in a background thread
    # This prevents Render from killing the bot for "no open port"
    t = threading.Thread(target=run_web_server)
    t.start()

    # 2. Start your Bot Logic
    main()