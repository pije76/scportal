# Using the SD card

## 1) Download the ready-to-go SD card image:

**Latest - emonSD-17-06-15.img.zip **

[Download UK Mirror](http://openenergymonitor.org/files/emonSD-17Jun2015.img.zip)

[Download USA Mirror](http://oem.aluminumalloyboats.com/oem/emonSD-17Jun2015.img.zip)


[See image User Guide Here](http://openenergymonitor.org/emon/modules/emonpi)

 
*Please get in contact if you can help with hosting bandwidth or seeding a torrent for these image downloads. Any help is much appreciated.*

### 1a) Alternatively build it yourself:

[https://github.com/emoncms/emoncms/blob/bufferedwrite/docs/install.md](https://github.com/emoncms/emoncms/blob/bufferedwrite/docs/install.md)

## 2) Write the image to an SD card

### Linux

Start by inserting your SD card, your distribution should mount it automatically so the first step is to unmount the SD card and make a note of the SD card device name, to view mounted disks and partitions run:

    $ df -h

You should see something like this:

    Filesystem            Size  Used Avail Use% Mounted on
    /dev/sda6             120G   90G   24G  79% /
    none                  490M  700K  490M   1% /dev
    none                  497M  1.7M  495M   1% /dev/shm
    none                  497M  260K  497M   1% /var/run
    none                  497M     0  497M   0% /var/lock
    /dev/sdb1             3.7G  4.0K  3.7G   1% /media/sandisk

Unmount the SD card, change sdb to match your SD card drive:

    $ umount /dev/sdb1 

If the card has more than one partition unmount that also: 

    $ umount /dev/sdb2

Locate the directory of your downloaded emoncms image in terminal and write it to an SD card using linux tool *dd*:

**Warning: take care with running the following command that your pointing at the right drive! If you point at your computer drive you could lose your data!**

    $ sudo dd bs=4M if=emonSD-17-06-15.img of=/dev/sdb

### Windows 

The main raspberry pi sd card setup guide recommends Win32DiskImager, see steps for windows here: 
[http://elinux.org/RPi_Easy_SD_Card_Setup](http://elinux.org/RPi_Easy_SD_Card_Setup)
Select the image as downloaded above.

### Mac OSX 

See steps for Mac OSX as documented on the main raspberry pi sd card setup guide:
[http://elinux.org/RPi_Easy_SD_Card_Setup](http://elinux.org/RPi_Easy_SD_Card_Setup)
Select the image as downloaded above.
<br><br>

## 3.) Getting Started User Guide:

[See emonHub / emonPi user guide here](http://openenergymonitor.org/emon/modules/emonpi)

