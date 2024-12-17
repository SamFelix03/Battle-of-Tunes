import telebot
from web3 import Web3

# Telegram Bot Token
BOT_TOKEN = "7718479528:AAFAjBQb6Eutn-BskyJRyx0Jz1giJVWLVS4"
bot = telebot.TeleBot(BOT_TOKEN)

# Binance Smart Chain Testnet RPC URL
BSC_TESTNET_RPC = "https://data-seed-prebsc-1-s1.binance.org:8545"
web3 = Web3(Web3.HTTPProvider(BSC_TESTNET_RPC))

# Deployed Contract Address and ABI
CONTRACT_ADDRESS = Web3.to_checksum_address("0x242c0c356cbaea0e1a80a574f1d3571a0babe772")
CONTRACT_ABI = [
    {
        "inputs": [],
        "name": "stake",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "verifyStake",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
]

contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

# Group Invite Link
GROUP_INVITE_LINK = "https://t.me/+ImTq8tu-h_82N2Y9"

@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "Welcome! Please send your wallet address to verify staking.")

@bot.message_handler(func=lambda msg: True)
def verify_stake(message):
    user_wallet = message.text.strip()

    # Validate wallet address
    if not Web3.is_address(user_wallet):
        bot.reply_to(message, "Invalid wallet address. Please try again.")
        return

    # Check if the user has staked
    try:
        has_staked = contract.functions.verifyStake(user_wallet).call()
        if has_staked:
            # Send the group invite link
            bot.reply_to(message, "Staking verified! Here is your invite link to join the group:")
            bot.send_message(message.chat.id, GROUP_INVITE_LINK)
        else:
            bot.reply_to(message, "You have not staked the required amount.")
    except Exception as e:
        bot.reply_to(message, f"Error verifying stake: {e}")

# Run the bot
print("Bot is running...")
bot.polling()