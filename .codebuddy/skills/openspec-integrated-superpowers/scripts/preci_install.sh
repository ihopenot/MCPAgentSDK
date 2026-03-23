#!/bin/bash

pathTo=$1
#企业微信号
user=$2
#pin+token
password=$3
install_path=~/PreCI

if [ ! $pathTo ]; then
  read -p "请输入PreCI安装路径(默认$install_path)：" pathTo
fi

if [ ! $pathTo ]; then
  install_path=~/PreCI
else
  install_path=$pathTo/PreCI
fi
mkdir -p $install_path

echo "installing PreCI into $install_path"

function addRunAtLoad()
{
  endOfF=EOF
  echo "add run at load to ~/Library/LaunchAgents/preci_server.plist!"
  mkdir -p ~/Library/LaunchAgents
  cat > ~/Library/LaunchAgents/preci_server.plist <<$endOfF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
        <string>preci_server</string>

    <key>ProgramArguments</key>
    <array>
        <string>$install_path/agent/jdk/Contents/Home/bin/java</string>
        <string>-Dfile.encoding=utf8</string>
        <string>-Durl=127.0.0.1:22101</string>
        <string>-DpreciDir=$install_path</string>
        <string>-jar</string>
        <string>$install_path/libs/preci_server.jar</string>
    </array>
    <key>RunAtLoad</key>
    <true/>

    <key>WorkingDirectory</key>
        <string>$install_path</string>
    <key>KeepAlive</key>
        <false/>
</dict>
</plist>
$endOfF
}

if [ "$(uname)" == "Darwin" ]; then
  if [ "$(uname -m)" == "arm64" ]; then
    curl -o $install_path/preci_bak "https://bkrepo.woa.com/generic/bkdevops/static/gw/resource/preci/prod2.24/darwin/arm64/preci"
  else
    curl -o $install_path/preci_bak "https://bkrepo.woa.com/generic/bkdevops/static/gw/resource/preci/prod2.24/darwin/preci"
  fi
elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
  curl -o $install_path/preci_bak "https://bkrepo.woa.com/generic/bkdevops/static/gw/resource/preci/prod2.24/linux/preci"
fi

if [ -f $install_path/preci_bak ]; then
  chmod -R 755 $install_path/preci_bak
  $install_path/preci_bak server --stop
  mv $install_path/preci_bak $install_path/preci
fi

if [ -f $install_path/preci ]; then
  chmod -R 755 $install_path/preci
  if [ "$(uname)" == "Darwin" ]; then
    touch ~/.bash_profile
    profile_result=`cat ~/.bash_profile |grep "export PATH" |grep "PreCI"`
    if [ "$profile_result" = "" ]; then
      echo export PATH=$install_path:\$PATH >> ~/.bash_profile
    else
      sed -e '/PreCI/d' ~/.bash_profile > ~/.bash_profile_bak
      echo export PATH=$install_path:\$PATH >> ~/.bash_profile_bak
      mv ~/.bash_profile_bak ~/.bash_profile
    fi
    source ~/.bash_profile
  elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
    mkdir -p ~/bin
    if [ -f ~/bin/preci ]; then
      unlink ~/bin/preci
    fi
    ln -s $install_path/preci ~/bin/preci
  fi

  touch ~/.zshrc
  zsh_result=`cat ~/.zshrc |grep "export PATH" |grep "PreCI"`
  if [ "$zsh_result" = "" ]; then
      echo export PATH=$install_path:\$PATH >> ~/.zshrc
  else
      sed -e '/PreCI/d' ~/.zshrc > ~/.zshrc_bak
      echo export PATH=$install_path:\$PATH >> ~/.zshrc_bak
      mv ~/.zshrc_bak ~/.zshrc
  fi
  source ~/.zshrc

  if [ "$user" != "" ] && [ "$password" != "" ]; then
    preci server --restart --user $user --password $password
  else
    preci server --restart
  fi

  if [ "$(uname)" == "Darwin" ]; then
    addRunAtLoad
  fi
  echo "PreCI is installed successfully"
  echo "首次安装请运行：source ~/.zshrc"
  echo "use command: preci --help"
else
  echo "Can't found the preci binary, check the error"
fi
