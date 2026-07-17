<p align="center"><a href="CONNECT_PHONE.md">📖 中文文档</a></p>

# Connect your phone · TypMic

## Android

1. Scan the QR code on the page, or just type the URL.
2. When the browser warns "certificate risk / not secure", tap "Advanced → Proceed" — it works normally.

## iPhone *(these steps are iPhone-only; Android needs none of them)*

The self-signed certificate already includes the LAN IP in its SAN and is valid for ≤398 days, so it complies with Apple's requirements — but iOS still needs manual trust.

### Step 1 — Send the root cert to the iPhone

1. The cert file is `rootCA.pem` in the **project root** on the server.
2. Send `rootCA.pem` to the iPhone via AirDrop / Mail / WeChat Files / cloud drive — anything works.
3. Open the file on the iPhone (or from the Files app) and **install the profile** when prompted. If it doesn't auto-open, go to **Settings → General → VPN & Device Management** (called "Profiles" on older iOS) and tap to install manually.

### Step 2 — Enable "full trust" for the certificate

**Installing the profile alone is not enough.** Go to **Settings → General → About → Certificate Trust Settings**, find this project's self-signed certificate, and **manually turn on the "Full Trust" switch**. Without this step, Safari still treats the connection as insecure and refuses to connect.

### Step 3 — Open the page

Once the certificate is trusted, open `https://<PC-IP>:8443` on the iPhone (or scan the QR code shown at `https://<PC-IP>:8443/desktop` on the PC). The address bar no longer shows a certificate warning, and you can press-and-hold to talk.
