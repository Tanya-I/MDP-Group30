# TASK 2
## To connect to rpi 

1. Connect to the rpi wifi MDPGrp30 , password :mdpgroup30
2. Go to terminal and type ssh pi@192.168.30.1 (the only space is between ssh and pi)
3. It will ask for password , which is mdpgroup30
4. cd Desktop (all the files are saved on Desktop)
5. ls to see all the file names 
6. task2_aryaman.py file is what we are using for task 2 . It works on rpi side . This one doesnt stop the timer on android with stm command. 
7. task2_final.py has the timer stop. RUN THIS .
8. task2_wa.py is without the android . So just press enter to start .
9. For pc side , download task2_pc_aryaman.py and v1.pt (only these 2 files if you dont want to clone the whole repo) to the same folder.
10. Download all the requirements from requirements.txt 

## To start running the task 2 code 
1. Connect to rpi and go to Desktop 
2. sudo python3 filename.py . (example filename task2_aryaman.py)
3. Then once all the starting message pop up on the rpi, run the pc code on your laptop. This should continuously say [PC] ⚠ HTTP 404: No photo captured yet , because our code continuously polls for photos on the rpi. Once we take one photo it will get.
4. Then either connect to android and do start or just press enter and then everything happens automatically. No need to press anything else. To stop the rpi code just do control c. 

NOTE : Sometimes the pc code will just stop and not work properly , just switch to ntusecure wifi and connect back to the mdp , should be fine. Maybe control c to stop and then re run. 
