import os
import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import logging

logging.basicConfig(level=logging.INFO)

# Load bot token from environment variable
TOKEN = ""
ADMIN_ID = 7760174741  # Replace with your actual Telegram user ID
PAYPAL_ME_LINK = "https://www.paypal.me/LieslKempf"
PRODUCTS_FILE = "products.json"

# Load products from JSON file
def load_products():
    try:
        with open(PRODUCTS_FILE, "r") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    except Exception as e:
        print(f"Error loading products: {e}")
        return []

# Save products to JSON file
def save_products(products):
    with open(PRODUCTS_FILE, "w") as file:
        json.dump(products, file, indent=4)

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    products = load_products()
    keyboard = [[InlineKeyboardButton(p["name"], callback_data=f"product_{p['name']}")] for p in products]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("Welcome to the shop! Select a product:", reply_markup=reply_markup)

# Handle product selection
async def product_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    products = load_products()
    product_name = query.data.replace("product_", "")
    product = next((p for p in products if p["name"] == product_name), None)
    
    if product:
        price = str(product['price']).replace(",", ".")  # Ensure correct decimal format
        pay_link = f"{PAYPAL_ME_LINK}/{price}"
        await query.message.reply_text(
            f"🛍 *{product['name']}*\n💬 {product['description']}\n💲 {product['price']}\n\n[💰 Pay Now]({pay_link})\nAfter payment, send proof of transaction.",
            parse_mode="Markdown"
        )

# ADMIN COMMANDS
async def admin_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 You are not authorized.")

    await update.message.reply_text("Enter the product details as: `name | description | price`", parse_mode="Markdown")
    context.user_data["adding_product"] = True

async def admin_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 You are not authorized.")

    products = load_products()
    if not products:
        return await update.message.reply_text("No products found.")

    keyboard = [[InlineKeyboardButton(p["name"], callback_data=f"edit_{p['name']}")] for p in products]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select a product to edit:", reply_markup=reply_markup)

async def admin_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 You are not authorized.")

    products = load_products()
    if not products:
        return await update.message.reply_text("No products found.")

    keyboard = [[InlineKeyboardButton(p["name"], callback_data=f"delete_{p['name']}")] for p in products]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select a product to delete:", reply_markup=reply_markup)

async def admin_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 You are not authorized.")

    products = load_products()
    if not products:
        return await update.message.reply_text("No products found.")

    product_list = "\n".join([f"🛍 {p['name']} - 💲{p['price']}" for p in products])
    await update.message.reply_text(f"📝 *Product List:*\n{product_list}", parse_mode="MarkdownV2")

# Handle adding and editing products
async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "adding_product" in context.user_data and context.user_data["adding_product"]:
        context.user_data["adding_product"] = False
        product_details = update.message.text.split("|")
        
        if len(product_details) != 3:
            return await update.message.reply_text("Invalid format. Use: `name | description | price`", parse_mode="Markdown")

        name, description, price = map(str.strip, product_details)
        products = load_products()
        products.append({"name": name, "description": description, "price": price})
        save_products(products)

        await update.message.reply_text(f"✅ Product '{name}' added successfully!")

    elif "editing_product" in context.user_data:
        old_name = context.user_data["editing_product"]
        product_details = update.message.text.split("|")

        if len(product_details) != 3:
            return await update.message.reply_text("Invalid format. Use: `name | description | price`", parse_mode="Markdown")

        new_name, description, price = map(str.strip, product_details)
        products = load_products()

        for product in products:
            if product["name"] == old_name:
                product["name"] = new_name
                product["description"] = description
                product["price"] = price
                break

        save_products(products)
        del context.user_data["editing_product"]
        await update.message.reply_text(f"✅ Product '{old_name}' updated successfully!")

# Handle product edits
async def edit_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_name = query.data.replace("edit_", "")

    context.user_data["editing_product"] = product_name
    await query.message.reply_text(f"Send new details for {product_name} as: `name | description | price`")

# Handle delete confirmation
async def delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_name = query.data.replace("delete_", "")

    products = load_products()
    products = [p for p in products if p["name"] != product_name]
    save_products(products)

    await query.message.reply_text(f"🗑 Product '{product_name}' deleted successfully!")

# Main function
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", admin_add))
    app.add_handler(CommandHandler("edit", admin_edit))
    app.add_handler(CommandHandler("delete", admin_delete))
    app.add_handler(CommandHandler("list", admin_list))
    app.add_handler(CallbackQueryHandler(product_selected, pattern="^product_"))
    app.add_handler(CallbackQueryHandler(edit_product, pattern="^edit_"))
    app.add_handler(CallbackQueryHandler(delete_product, pattern="^delete_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
