
####################################################################################################
# ubuntu开启ssh服务，termux连接
####################################################################################################

# ubuntu

# 更新源
sudo apt update
# 安装SSH服务端
sudo apt install -y openssh-server
# 查看状态（显示active即正常）
sudo systemctl status ssh
# 开机自启（可选）
sudo systemctl enable ssh

# Termux
pkg update
pkg install -y openssh

termux-setup-storage
# 手机弹窗点“允许”，否则传不了手机里的文件




####################################################################################################
# Termux 开启 SSH 服务，Ubuntu 就能反向连接、scp 互传文件
####################################################################################################
# termux
sshd
passwd
whoami

# ubuntu
# 格式：ssh termux用户名@TermuxIP -p 8022
ssh u0_axxx@192.168.x.x -p 8022