Các lệnh cần chạy


```

git clone https://github.com/tungdv24/IP-Page.git

cd IP-Page

python3 -m venv venv

source venv/bin/activate

pip install -r requirements.txt

python3 database.py

python3 app.py

```

Tạo service

```
sudo nano /etc/systemd/system/all-ip-app.service

sudo systemctl daemon-reload

systemctl start all-ip-app.service

systemctl enable all-ip-app.service

systemctl status all-ip-app.service
```