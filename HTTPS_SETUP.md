# HTTPS Setup (Let's Encrypt)

This project uses NGINX + Let's Encrypt for HTTPS.

---

## 1. Prerequisites

- Domain pointing to server IP
- HTTP working:
  http://yourdomain.com
- Ports open:
  sudo ufw allow 80
  sudo ufw allow 443

---

## 2. Install Certbot

sudo apt update  
sudo apt install certbot -y

---

## 3. Stop NGINX container

docker compose stop nginx

---

## 4. Generate certificate

Replace yourdomain.com:

sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

Certificates are stored at:

/etc/letsencrypt/live/yourdomain.com/

---

## 5. Check docker-compose.yml

Ensure nginx has:

ports:
  - "80:80"
  - "443:443"

volumes:
  - ./nginx.conf:/etc/nginx/nginx.conf:ro
  - /etc/letsencrypt:/etc/letsencrypt:ro

---

## 6. Check nginx.conf

Ensure an HTTPS server exists like:

server {
    listen 443 ssl;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

---

## 7. Restart containers

docker compose up -d

---

## 8. Test HTTPS

curl -I https://yourdomain.com

---

## 9. Renewal

Certificates auto-renew.

Test:

docker compose stop nginx
sudo certbot renew --dry-run
docker compose start nginx

---

## Notes
- Certificates are valid for 90 days
- During renewal (standalone mode), port 80 must be free
