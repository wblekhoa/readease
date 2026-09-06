#!/bin/bash
# Tạo chứng chỉ ký mã CỐ ĐỊNH "ReadEase Dev" trong login keychain, để build lại
# KHÔNG rụng quyền Trợ năng. Chạy MỘT lần; macOS sẽ hỏi mật khẩu đăng nhập ở
# bước đặt tin cậy.
#
# Vì sao: ký ad-hoc thì "yêu cầu định danh" (designated requirement) của app là
# cdhash — hash của chính binary. Build lại là hash khác, nên TCC coi đây là một
# app khác và quyền đã cấp không còn khớp; dòng trong Cài đặt hệ thống vẫn nằm
# đó nhưng đã chết. Ký bằng một chứng chỉ cố định thì yêu cầu trở thành
# "identifier + chứng chỉ", không đổi giữa các lần build.
#
# Chứng chỉ này CHỈ dành cho bản cài trên máy này. Nó không giúp gì cho
# Gatekeeper ở máy người khác, và bản phát hành (scripts/build-release-app.sh)
# cố ý KHÔNG dùng nó — thứ rời khỏi máy vẫn ad-hoc như trước.
#
# Cách 2, không cần Terminal: Keychain Access → Certificate Assistant →
# Create a Certificate… → Name "ReadEase Dev", Identity Type "Self Signed Root",
# Certificate Type "Code Signing".
set -euo pipefail
NAME="${1:-ReadEase Dev}"
KC="$HOME/Library/Keychains/login.keychain-db"

if security find-identity -v -p codesigning "$KC" 2>/dev/null | grep -q "\"$NAME\""; then
  echo "✔ Đã có chứng chỉ \"$NAME\" hợp lệ — không cần tạo."
  exit 0
fi

T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
cat > "$T/cert.cnf" <<CNF
[req]
distinguished_name = dn
x509_extensions = ext
prompt = no
[dn]
CN = $NAME
[ext]
keyUsage = critical, digitalSignature
extendedKeyUsage = critical, codeSigning
basicConstraints = critical, CA:false
subjectKeyIdentifier = hash
CNF

echo "▶ Tạo khoá + chứng chỉ tự ký (10 năm)…"
openssl req -x509 -newkey rsa:2048 -sha256 -days 3650 -nodes \
  -keyout "$T/key.pem" -out "$T/cert.pem" -config "$T/cert.cnf" >/dev/null 2>&1

# Cụm mật khẩu chỉ sống trong thư mục tạm này, dùng để chuyển khoá vào keychain.
PASS="readease-local-$RANDOM"
openssl pkcs12 -export -inkey "$T/key.pem" -in "$T/cert.pem" -out "$T/dev.p12" \
  -passout "pass:$PASS" -legacy >/dev/null 2>&1 \
  || openssl pkcs12 -export -inkey "$T/key.pem" -in "$T/cert.pem" -out "$T/dev.p12" \
       -passout "pass:$PASS" >/dev/null 2>&1

echo "▶ Nhập vào login keychain…"
security import "$T/dev.p12" -k "$KC" -P "$PASS" -T /usr/bin/codesign -T /usr/bin/security >/dev/null

echo "▶ Đặt tin cậy cho ký mã (macOS sẽ hỏi mật khẩu đăng nhập)…"
security add-trusted-cert -r trustRoot -p codeSign -k "$KC" "$T/cert.pem"

if security find-identity -v -p codesigning "$KC" | grep -q "\"$NAME\""; then
  echo "✔ Xong. Từ giờ scripts/install-local-app.sh tự ký bằng \"$NAME\"."
  echo "  Lần cài kế: bỏ ReadEase khỏi Trợ năng rồi thêm lại MỘT lần cuối — sau đó quyền giữ mãi."
  echo
  echo "  CÒN MỘT BƯỚC nếu không muốn bị hỏi mật khẩu mỗi lần ký. Khoá nhập bằng"
  echo "  \`security import\` bị một lớp thứ hai (partition list) chặn, nên nút"
  echo "  \"Always Allow\" trong hộp thoại KHÔNG dính. Chạy dòng này trong Terminal"
  echo "  CỦA BẠN (nó tự hỏi mật khẩu; đừng đưa mật khẩu cho công cụ nào khác):"
  echo
  echo "    security set-key-partition-list -S apple-tool:,apple:,codesign: -s -t private \\"
  echo "      ~/Library/Keychains/login.keychain-db"
  echo
  echo "  Một lần cho cả máy — nó áp cho mọi khoá ký trong login keychain."
else
  echo "✗ Chứng chỉ chưa được coi là hợp lệ. Mở Keychain Access → login → Certificates →" >&2
  echo "  \"$NAME\" → Get Info → Trust → Code Signing: Always Trust." >&2
  exit 1
fi
