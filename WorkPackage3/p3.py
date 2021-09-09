# Import libraries
import RPi.GPIO as GPIO
import random
import ES2EEPROMUtils
import os
import time

# some global variables that need to change as we run the program
end_of_game = None  # set if the user wins or ends the game
value = 0
compareValue = 0
sleepTime = 0
guessVal = 0
totalGuesses = 0
loadedScores = []

# DEFINE THE PINS USED HERE
LED_value = [11, 13, 15]
LED_accuracy = 32
btn_submit = 16
btn_increase = 18
buzzer = 33
eeprom = ES2EEPROMUtils.ES2EEPROM()


# Print the game banner
def welcome():
    os.system('clear')
    print("  _   _                 _                  _____ _            __  __ _")
    print("| \ | |               | |                / ____| |          / _|/ _| |")
    print("|  \| |_   _ _ __ ___ | |__   ___ _ __  | (___ | |__  _   _| |_| |_| | ___ ")
    print("| . ` | | | | '_ ` _ \| '_ \ / _ \ '__|  \___ \| '_ \| | | |  _|  _| |/ _ \\")
    print("| |\  | |_| | | | | | | |_) |  __/ |     ____) | | | | |_| | | | | | |  __/")
    print("|_| \_|\__,_|_| |_| |_|_.__/ \___|_|    |_____/|_| |_|\__,_|_| |_| |_|\___|")
    print("")
    print("Guess the number and immortalise your name in the High Score Hall of Fame!")


# Print the game menu
def menu():
    global end_of_game
    global value
    option = input("Select an option:   H - View High Scores     P - Play Game       Q - Quit\n")
    option = option.upper()

  
    if option == "H":
        os.system('clear')
        print("HIGH SCORES!!")
        s_count, ss = fetch_scores()
        display_scores(s_count, ss)
    elif option == "P":
        os.system('clear')
        print("Starting a new round!")
        print("Use the buttons on the Pi to make and submit your guess!")
        print("Press and hold the guess button to cancel your game")
        value = generate_number()
        totalGuesses = 0
        print(value)
        while not end_of_game:
            pass
    elif option == "Q":
        print("Come back soon!")
        exit()
    else:
        print("Invalid option. Please select a valid one!")


def display_scores(count, raw_data):
    # print the scores to the screen in the expected format
    print("There are", count, " scores. Here are the top 3!")
    for i in range(3):
        print(i,"-", raw_data[i][0] + raw_data[i][1] + raw_data[i][2], "took" ,raw_data[i][3] , "guesses")

    # print out the scores in the required format
    pass


# Setup Pins
def setup():
    global pwmLED
    global pwm
    # Setup board mode
    GPIO.setmode(GPIO.BOARD)
    # Setup regular GPIO
    GPIO.setup(buzzer, GPIO.OUT)
    GPIO.setup(LED_value, GPIO.OUT)
    GPIO.setup(LED_accuracy,GPIO.OUT)
    # Setup PWM channels
    pwmLED = GPIO.PWM(LED_accuracy,1000)
    pwmLED.start(0)
 
    pwm = GPIO.PWM(buzzer, 1)
    pwm.start(0)
    pwm.ChangeDutyCycle(0)
    # Setup debouncing and callbacks
    GPIO.setup(btn_increase,GPIO.IN,pull_up_down=GPIO.PUD_UP)
    GPIO.setup(btn_submit,GPIO.IN,pull_up_down=GPIO.PUD_UP)

    GPIO.add_event_detect(btn_increase, GPIO.FALLING,
                          callback=btn_increase_pressed,
                          bouncetime=400)
    GPIO.add_event_detect(btn_submit, GPIO.FALLING,
                          callback=btn_guess_pressed,
                          bouncetime=400)

    pass


# Load high scores
def fetch_scores():
    # get however many scores there are
    score_count = None
    # Get the scores
    i = 1
    scores = []
    score_count = eeprom.read_block(0,1)[0]
    while eeprom.read_block(i,4) != [0,0,0,0]:
        scores.append(eeprom.read_block(i,4))
        i += 1
    # convert the codes back to ascii
    for i in range(len(scores)):
        scores[i][0] = chr(scores[i][0])
        scores[i][1] = chr(scores[i][1])
        scores[i][2] = chr(scores[i][2])
    # return back the results
    return score_count, scores


# Save high scores
def save_scores():    
    # fetch scores
    global totalGuesses
    s_count, ss = fetch_scores()
    # include new score
    username = "xxxx"
    while len(username) > 3:
        username = input("Please enter a 3 letter name for your score to be recorded.")
    tempArr = list(username)
    tempArr.append(totalGuesses)
    ss.append(tempArr)
    # sort
    for i in range(len(ss)-1):
        for j in range(len(ss)- i - 1):
            if ss[j][3] > ss[j+1][3]:
                tempArr = ss[j]
                ss[j] = ss[j+1]
                ss[j+1] = tempArr

    # update total amount of scores
    s_count += 1
    # write new scores
    eeprom.clear(2048)
    eeprom.write_block(0,[s_count,0,0,0])
    for i in range(len(ss)):
        ss[i][0] = ord(ss[i][0])
        ss[i][1] = ord(ss[i][1])
        ss[i][2] = ord(ss[i][2])
        eeprom.write_block(i+1,ss[i])
    menu()
    pass


# Generate guess number
def generate_number():
    return random.randint(0, pow(2, 3)-1)


# Increase button pressed
def btn_increase_pressed(channel):
    # Increase the value shown on the LEDs
    # You can choose to have a global variable store the user's current guess, 
    # or just pull the value off the LEDs when a user makes a guess
    global guessVal
    guessVal =  0
    if GPIO.input(11):
        guessVal = guessVal + 1
    if GPIO.input(13):
        guessVal = guessVal + 2
    if GPIO.input(15):
        guessVal = guessVal + 4
    if guessVal == 7:
        GPIO.output(11,0)
        GPIO.output(13,0)
        GPIO.output(15,0)
        guessVal = -1
    guessVal = guessVal + 1
    binVal = f'{guessVal:03b}'
    GPIO.output(11,int(binVal[2]))
    GPIO.output(13,int(binVal[1]))
    GPIO.output(15,int(binVal[0]))
    pass


# Guess button
def btn_guess_pressed(channel):
    # If they've pressed and held the button, clear up the GPIO and take them back to the menu screen
    # Compare the actual value with the user value displayed on the LEDs
    global comparedValue
    global guessVal
    global pwm
    global pwmLED
    global totalGuesses
    
    start_time = time.time()

    while GPIO.input(channel) == 0: # Wait for the button up
        pass

    buttonTime = time.time() - start_time

    if 0.05 < buttonTime < 0.35:
        comparedValue = abs(value-guessVal)	
        totalGuesses += 1
        if comparedValue == 0:
            pwm.ChangeDutyCycle(0)
            pwmLED.ChangeDutyCycle(0)
            print("You have guessed correctly and won the game!")
            print("It only took you ", totalGuesses, " guesses!")
            save_scores()
        else: 
            accuracy_leds()
            trigger_buzzer()
    else:
        GPIO.output([11,13,15,buzzer,LED_accuracy],0)
        pwm.ChangeDutyCycle(0)
        pwmLED.ChangeDutyCycle(0)
    # Change the PWM LED
    # if it's close enough, adjust the buzzer
    # if it's an exact guess:
    # - Disable LEDs and Buzzer
    # - tell the user and prompt them for a name
    # - fetch all the scores
    # - add the new score
    # - sort the scores
    # - Store the scores back to the EEPROM, being sure to update the score count
    pass


# LED Brightness
def accuracy_leds():
    # Set the brightness of the LED based on how close the guess is to the answer
    # - The % brightness should be directly proportional to the % "closeness"
    # - For example if the answer is 6 and a user guesses 4, the brightness should be at 4/6*100 = 66%
    # - If they guessed 7, the brightness would be at ((8-7)/(8-6)*100 = 50%
    global comparedValue
    global value
    global pwmLED
    global guessVal
    if guessVal < value:
        brightness = guessVal/value
    else:
        brightness = (8-guessVal)/(8-value)
    pwmLED.ChangeDutyCycle(round(brightness*100))
    pass

# Sound Buzzer
def trigger_buzzer():
    global pwm
    global comparedValue
    dutyCycle = 50
    freq = 1
    if comparedValue == 3:
        freq = 1
    else:
        if comparedValue == 2:
            freq = 2
        else:
            if comparedValue == 1:
                freq = 4
            else:
                dutyCycle = 0
    pwm.ChangeDutyCycle(dutyCycle)
    pwm.ChangeFrequency(freq)
    # The buzzer operates differently from the LED
    # While we want the brightness of the LED to change(duty cycle), we want the frequency of the buzzer to change
    # The buzzer duty cycle should be left at 50%
    # If the user is off by an absolute value of 3, the buzzer should sound once every second
    # If the user is off by an absolute value of 2, the buzzer should sound twice every second
    # If the user is off by an absolute value of 1, the buzzer should sound 4 times a second
    pass


if __name__ == "__main__":
    try:
        # Call setup function
        setup()
        welcome()
        while True:
            menu()
            pass
    except Exception as e:
        print(e)
    finally:
        GPIO.cleanup()
