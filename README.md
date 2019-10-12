# KFControl
KFControl
install :

cd ~/domoticz/plugins

mkdir KFControl

sudo apt-get update

sudo apt-get install git

git clone https://github.com/Erwanweb/KFControl.git KFControl

cd KFControl

sudo chmod +x plugin.py

sudo /etc/init.d/domoticz.sh restart

Upgrade :

cd ~/domoticz/plugins/KFControl

git reset --hard

git pull --force

sudo chmod +x plugin.py

sudo /etc/init.d/domoticz.sh restart
