# homebridge_baby_white_noise

## install

```bash
sudo apt update
sudo apt install mkchromecast python3-fastapi python3-uvicorn
```

## auto start

```
sudo cp baby_white_noise_google_cast.service /etc/systemd/system/baby_white_noise_google_cast.service
sudo systemctl enable baby_white_noise_google_cast.service
sudo systemctl start baby_white_noise_google_cast.service
sudo systemctl status baby_white_noise_google_cast.service
```

```
sudo cp ./homebridge_baby_white_noise.sh /var/lib/homebridge/node_modules/homebridge-cmd4/script/homebridge_baby_white_noise.sh
```
