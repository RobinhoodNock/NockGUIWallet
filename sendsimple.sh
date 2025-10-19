#!/bin/bash
GRPC_ARGS=(--client public --public-grpc-server-addr https://nockchain-api.zorp.io)
TXS_DIR="$(pwd)/txs"

echo "========================================"
echo "       Robinhood's Simple Send"
echo "========================================"
echo

# Parse optional --index argument
index=""
while [[ $# -gt 0 ]]; do
  case $1 in
    --index)
      index="$2"
      shift 2
      ;;
    *)
      break
      ;;
  esac
done

# Prompt inputs if not passed via stdin
read -rp $'📤 Sender pubkey:\n> ' sender
read -rp $'📥 Recipient pubkey:\n> ' recipient
read -rp $'🎁 Gift amount:\n> ' gift
read -rp $'💸 Fee amount:\n> ' fee

# Validate gift and fee are integers
if ! [[ "$gift" =~ ^[0-9]+$ ]] || ! [[ "$fee" =~ ^[0-9]+$ ]]; then
  echo "❌ Gift and fee must be integers."
  exit 1
fi

total=$((gift + fee))
echo -e "\n➕ Total amount needed (gift + fee): $total\n"

csvfile="notes-${sender}.csv"
echo "📂 Exporting notes CSV..."
if ! nockchain-wallet "${GRPC_ARGS[@]}" list-notes-by-pubkey-csv "$sender" >/dev/null 2>&1; then
  echo "❌ Failed to export notes CSV."
  exit 1
fi

echo -n "⏳ Waiting for notes file ($csvfile)... "
while [ ! -f "$csvfile" ]; do sleep 1; done
echo "Found!"

# Select notes until total assets cover required amount
selected_notes=()
selected_assets=0
while IFS=',' read -r name_first name_last assets block_height source_hash; do
  [[ "$name_first" == "name_first" ]] && continue
  selected_notes+=("$name_first $name_last")
  selected_assets=$((selected_assets + assets))
  if [ "$selected_assets" -ge "$total" ]; then break; fi
done < "$csvfile"

if [ "$selected_assets" -lt "$total" ]; then
  echo "❌ Insufficient funds: found $selected_assets, need $total"
  exit 1
fi

echo "✅ Selected notes: ${selected_notes[*]}"
echo "💰 Total assets selected: $selected_assets"

# Build --names argument
names_arg=""
for note in "${selected_notes[@]}"; do
  if [[ -n "$names_arg" ]]; then
    names_arg+=","
  fi
  names_arg+="[$note]"
done

# Build --recipients argument
recipients_arg="[1 $recipient]"

# Prepare transaction folder
mkdir -p "$TXS_DIR"
echo -e "\n🧹 Cleaning transaction folder ($TXS_DIR)..."
rm -f "$TXS_DIR"/*
echo "🗑️ Folder cleaned."

# Create transaction with conditional index argument
echo -e "\n🛠️ Creating draft transaction..."

if [[ -n "$index" ]]; then
  echo "Command: nockchain-wallet ${GRPC_ARGS[*]} create-tx --names $names_arg --recipients $recipients_arg --gifts $gift --fee $fee --index $index"
  if ! nockchain-wallet "${GRPC_ARGS[@]}" create-tx \
    --names "$names_arg" \
    --recipients "$recipients_arg" \
    --gifts $gift \
    --fee $fee \
    --index $index >/dev/null; then
    echo "❌ Failed to create draft transaction."
    exit 1
  fi
else
  echo "Command: nockchain-wallet ${GRPC_ARGS[*]} create-tx --names $names_arg --recipients $recipients_arg --gifts $gift --fee $fee"
  if ! nockchain-wallet "${GRPC_ARGS[@]}" create-tx \
    --names "$names_arg" \
    --recipients "$recipients_arg" \
    --gifts $gift \
    --fee $fee >/dev/null; then
    echo "❌ Failed to create draft transaction."
    exit 1
  fi
fi

# Pick any .tx file in txs directory
txfile=$(find "$TXS_DIR" -maxdepth 1 -type f -name '*.tx' | head -n 1)
if [[ -z "$txfile" ]]; then
  echo "❌ No transaction file found after creating draft."
  exit 1
fi

echo "✅ Draft transaction created: $txfile"

# Send TX
echo "🚀 Sending transaction..."
output=$(nockchain-wallet "${GRPC_ARGS[@]}" send-tx "$txfile")
if [[ $? -eq 0 ]]; then
  echo -e "\n📝 Transaction details:\n$output"
  echo "✅ Transaction sent successfully!"
else
  echo -e "\n❌ Error details:\n$output"
  echo "❌ Failed to send transaction."
fi
