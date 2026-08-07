# 🌐 Headscale + Headplane + Caddy Stack

A complete, production-ready Docker Compose stack for self-hosting a WireGuard-based mesh VPN.

Securely connect your servers, virtual machines, and personal devices into a private network. It leverages Headscale for WireGuard networking, Headplane for a modern web UI, and Caddy for automatic HTTPS, alongside a custom Python update notifier.

## ✨ Features

* **Headscale (v0.29.2):** Open-source, self-hosted Tailscale control server for establishing WireGuard tunnels.
* **Headplane:** Beautiful Web UI for managing nodes, users, routing, and pre-auth keys.
* **Caddy:** Reverse proxy for automatic HTTPS, secure routing, and SSL/TLS certificate renewals via Let's Encrypt.
* **Update Notifier:** Python daemon that monitors juanfont/headscale GitHub releases and sends Discord alerts for updates and breaking changes.

## 📋 Prerequisites & Cloud Networking

This guide specifically covers the network configuration for **Oracle Cloud (Ubuntu)**, but the steps will be similar for other cloud providers (AWS, GCP, Azure, DigitalOcean).

### 1. DNS Configuration
* A registered domain name (e.g., `headscale.yourdomain.com`).
* An **A-Record** in your DNS provider pointing to your cloud VM's public IP address.
* **Cloudflare Users:** You **MUST** set the record to **"DNS Only"**. Proxying the record will break WireGuard's direct peer-to-peer UDP connections.

### 2. Firewall & Open Ports
You must open the following ports to allow traffic. **For Oracle Cloud:** You must allow these ports in *both* the Oracle Cloud Dashboard (VCN Security Lists) and the local Ubuntu OS firewall.

* **TCP 80:** Caddy reverse proxy (HTTP -> HTTPS redirection and Let's Encrypt SSL challenges).
* **TCP 443:** Caddy reverse proxy (Headscale API, Headplane UI, and DERP fallback).
* **UDP 3478:** Headscale built-in STUN/DERP server (Crucial for NAT traversal).

**Ubuntu `iptables` rules (Oracle Cloud default is "two-layer" security, which makes these rules REQUIRED):**
```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p udp --dport 3478 -j ACCEPT
sudo netfilter-persistent save
```

## 🚀 Quick Start (Deploying via Docker)

Follow these steps to deploy the stack on your own server.

1. Clone the repository:

```bash
git clone https://github.com/hanafytech/headscale-stack.git
cd headscale-stack
```

2. Create the necessary directories and download the base Headscale config:

```bash
mkdir -p config data headplane-data headplane-config caddy_data caddy_config notifier-data
wget -O config/config.yaml https://raw.githubusercontent.com/juanfont/headscale/main/config-example.yaml
```

&emsp;&ensp; ***Edit `config/config.yaml` and set `server_url: https://headscale.yourdomain.com`.*
*Change the listen address to `listen_addr: 0.0.0.0:8080` (otherwise Caddy cannot route traffic to the container)!***

3. Configure the Built-in DERP Server (Firewall Bypass)
In `config/config.yaml`, scroll to the `derp:` section. You must make three critical changes to bypass restrictive firewalls and prevent connection failures:
* Set `enabled: true` to turn on the embedded server.
* Comment out the `ipv4` and `ipv6` fields. **(Important: You must comment out or remove the default `198.51.100.1` and `2001:db8::1` dummy IPs, or your clients will attempt to route traffic to fake addresses and fail).**
* Empty the official relay list by setting `urls: []` and commenting out the default Tailscale URL.

Modify the block to match this:
```yaml
derp:
  server:
    enabled: true
    region_id: 999
    region_code: "headscale"
    region_name: "Headscale Embedded DERP"
    verify_clients: true
    stun_listen_addr: "0.0.0.0:3478"
    private_key_path: /var/lib/headscale/derp_server_private.key
    automatically_add_embedded_derp_region: true
    # ipv4: 198.51.100.1
    # ipv6: 2001:db8::1
  urls: []
  #  - [https://controlplane.tailscale.com/derpmap/default](https://controlplane.tailscale.com/derpmap/default)
  paths: []
  auto_update_enabled: true
  update_frequency: 3h
```

4. Create `headplane-config/config.yaml` and populate it with your settings:
   *(Note: The `public_url` variable is crucial! It ensures the "Register Machine Key" UI displays your actual domain instead of internal Docker IPs).*


```yaml
server:
  host: "0.0.0.0"
  port: 3000
  cookie_secret: "GENERATE_A_RANDOM_32_CHARACTER_SECURE_STRING_HERE"

headscale:
  url: "http://headscale:8080"
  public_url: "https://headscale.yourdomain.com"
  config_path: "/etc/headscale/config.yaml"
```

5. Update External Variables:
   * **Caddyfile:** Open the `Caddyfile` and ensure your domain is correct.
   * **Discord Notifier (Optional):** Open `docker-compose.yaml` and replace `your_webhook_url_here` under the `notifier` service with your actual Discord Webhook URL.

6. Deploy the stack:

```bash
docker compose pull
docker compose up -d
```

## 📝 How to Use

1. To log into Headplane for the first time, generate an API key directly from the Headscale container:
```bash
docker exec headscale headscale apikeys create --expiration 90d
```
2. Navigate to your deployed domain (e.g., `https://headscale.yourdomain.com/admin`).
3. Enter the generated API key into the login screen to authenticate.
4. Create your first user. You can do this in the Headplane UI under the "Users" tab, or via the command line:
```bash
docker exec headscale headscale users create myuser
```
5. Install the Tailscale client on the device you want to connect.
   * **For Linux:**
     ```bash
     curl -fsSL https://tailscale.com/install.sh | sh
     ```
   * **For Windows/macOS/Mobile:** Download the app from the [Tailscale website](https://tailscale.com/download).

6. Once installed, connect the device to your custom VPN by running the following in your client's terminal:

```bash
tailscale up --login-server https://headscale.yourdomain.com
```
7. The terminal will output a machine key/registration link. Copy it, go to the Headplane UI, click **Add Device -> Register Machine Key**, paste the key, and select your user to authenticate the device!

### Optional: Use a reusable pre-authentication key (recommended for multiple devices)

If you plan on registering multiple devices, you can generate a reusable pre-authentication key on your Headscale server instead of completing the browser-based login for each device.

Generate a reusable pre-authentication key:

```bash
docker exec headscale headscale preauthkeys create --user 1 --reusable --expiration 24h
```

> **Note:** Replace `1` with the ID of the Headscale user you want to register the device under.

The command will return an auth key similar to:

```text
hskey-auth-1234567890
```

You can then register devices directly by running:

```bash
tailscale up --login-server https://headscale.yourdomain.com --authkey hskey-auth-1234567890
```



## 💻 Tech Stack

* **VPN Control Server:** Headscale (Go)
* **Web Interface:** Headplane (Node.js/SvelteKit)
* **Reverse Proxy:** Caddy (Go)
* **Scripting:** Python 3.11
* **Containerization:** Docker