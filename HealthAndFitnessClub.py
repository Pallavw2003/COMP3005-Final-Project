import psycopg2
import re
from datetime import datetime

db_user = 'postgres'
db_password = 'postgres'
db_host = 'localhost'
db_port = 5432
db_database = 'HealthAndFitnessClubManagementSystem'
connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_database}"

# Establishing a connection to the database
try:
    connection = psycopg2.connect(connection_string)
    print(f"Connected to the {db_database} database as user {db_user}\n")

    #---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Defining the checkTrainerAvailibility helper function which helps us determine if the trainer is available and not busy with a PT session or a class at a given date/time.
    #---------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    def checkTrainerAvailability(trainerId, date, startTime, endTime):
        try:
            cursor = connection.cursor()

            # Check if the trainer is available at the specified time by seeing if the whole class (startTime to endTime) is contained in one of the user's TrainerAvailibility entries
            cursor.execute("""
                SELECT COUNT(*) 
                FROM TrainerAvailability 
                WHERE trainerId = %s AND availabilityDate = %s AND startTime <= %s AND endTime >= %s
            """, (trainerId, date, startTime, endTime))

            availabilityCount = cursor.fetchone()[0]

            if availabilityCount == 0:
                print(f"Trainer #{trainerId} does not have availibility at this time")
                return False

            # Check if the trainer is already teaching a class at the same time
            cursor.execute("""
                SELECT COUNT(*) 
                FROM Class 
                WHERE trainerId = %s AND classDate = %s 
                AND ((%s BETWEEN startTime AND endTime) OR (%s BETWEEN startTime AND endTime) OR (%s < startTime AND %s > endTime))
            """, (trainerId, date, startTime, endTime, startTime, endTime))

            overlappingClassesCount = cursor.fetchone()[0]
            if overlappingClassesCount > 0:
                print(f"This is overlapping with {overlappingClassesCount} of trainer #{trainerId}'s classes")
                return False
            
            # Check if the trainer has a personal training session at the same time
            cursor.execute("""
                SELECT COUNT(*) 
                FROM PersonalTrainingSession 
                WHERE trainerId = %s AND sessionDate = %s 
                AND ((%s BETWEEN startTime AND endTime) OR (%s BETWEEN startTime AND endTime) OR (%s < startTime AND %s > endTime))
            """, (trainerId, date, startTime, endTime, startTime, endTime))
            
            overlappingPtSessionsCount = cursor.fetchone()[0]
            if overlappingPtSessionsCount > 0:
                print(f"This is overlapping with {overlappingPtSessionsCount} of trainer #{trainerId}'s classes")
                return False

            # If none of the overlap conditions are met, returning true
            return True

        except psycopg2.Error as err:
            print("Error while checking trainer availability:", err)
        finally:
            cursor.close()

    #-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Defining the checkUserAvailability helper function which helps us determine if the member is available and not busy with a PT session or a class at a given date/time.
    #-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
    def checkUserAvailability(userId, date, startTime, endTime):
        try:
            cursor = connection.cursor()
            
            # Check if the user is already taking a class at the same time
            cursor.execute("""
                SELECT COUNT(*) 
                FROM MemberTakesClass 
                JOIN Class ON MemberTakesClass.classId = Class.classId 
                WHERE MemberTakesClass.userId = %s AND Class.classDate = %s 
                AND ((%s BETWEEN Class.startTime AND Class.endTime) OR (%s BETWEEN Class.startTime AND Class.endTime) OR (%s < Class.startTime AND %s > Class.endTime))
            """, (userId, date, startTime, endTime, startTime, endTime))

            overlappingClassesCount = cursor.fetchone()[0]
            if overlappingClassesCount > 0:
                print(f"This is overlapping with {overlappingClassesCount} of classes that the user is taking.")
                return False
            
            cursor.execute("""
                SELECT COUNT(*) 
                FROM PersonalTrainingSession 
                WHERE userId = %s AND sessionDate = %s 
                AND ((%s BETWEEN startTime AND endTime) OR (%s BETWEEN startTime AND endTime) OR (%s < startTime AND %s > endTime))
            """, (userId, date, startTime, endTime, startTime, endTime))

            overlappingPtSessionsCount = cursor.fetchone()[0]
            if overlappingPtSessionsCount > 0:
                print(f"This is overlapping with {overlappingPtSessionsCount} of personal training sessions that the user is taking.")
                return False

            return True
        
        except psycopg2.Error as err:
            print("Error while checking user availability:", err)
        finally:
            cursor.close()


    #------------------------------------------------------------------------------
    # Defining the isValidDate helper function for registerUser and for scheduling.
    #------------------------------------------------------------------------------
    def isValidDate(date, earliestYear):
        try:
            year, month, day = date.split('-')
            year = int(year)
            month = int(month)
            day = int(day)

            # earliestYear is the minimum year the user can enter for a specific date (for example, for birth days I don't want anyone born after 1901 as that is not realistic, so I will use that for earliestYear. For maintenance, assuming my gym opened on Jan 1, 2022 so that is the earliestYear)
            if month < 1 or month > 12 or day < 1 or day > 31 or year < earliestYear:
                return False
            if (month == 4 or month == 6 or month == 9 or month == 11) and day > 30: # if its a month with 30 days and day > 30
                return False
            if month == 2: # if its feb, determining if it is a leap year to determine the valid day
                if year % 4 == 0:
                    if day > 29:
                        return False
                elif day > 28:
                    return False
            return True
        except ValueError: # if the user enters something that's not an int for MM, DD, or YYYY
            return False

    #-----------------------------------------------------------------------------------------------------------------
    # Defining the registerUser function which asks the user various information and makes a DB insertion accordingly.
    #-----------------------------------------------------------------------------------------------------------------
    def registerUser():
        fName = input("Please enter your first name: ")
        lName = input("Please enter your last name: ")
        
        while True:
            email = input("Please enter your email address: ")

            # Determining if the email address is an actual email address
            if re.match(r'^[\w\.-]+@([\w-]+\.)+[\w-]{2,4}$', email):
                break
            else:
                print("You have entered an invalid email. Please try again")
        
        while True:
            password = input("Please enter your password (min 8 characters, including 1 letter and 1 number): ")

            # Determining if the password meets the required criteria
            if len(password) >= 8 and any(c.isalpha() for c in password) and any(c.isdigit() for c in password):
                break
            else:
                print("You have entered an invalid password. Please review the criteria and try again.")

        while True:
            dateOfBirth = input("Please enter your date of birth in the format YYYY-MM-DD: ")

            # Determining if the date of birth meets the required format and its a valid date
            if re.match(r'^\d{4}-\d{2}-\d{2}$', dateOfBirth):
                if isValidDate(dateOfBirth, 1901):
                    break
                else:
                    print("You have entered an invalid date of birth. Please enter a valid date after January 1, 1901.")
            else:
                print("You have entered an invalid date of birth. Please use the format YYYY-MM-DD (ex. 2003-04-15).")
                

        while True:
            phoneNumber = input("Please enter your phone number in the format (###) ###-####: ")
            
            if re.match(r'^\(\d{3}\) \d{3}-\d{4}$', phoneNumber):
                break
            else:
                print("You have entered an invalid phone number. Please use the format (###) ###-#### where # is a digit.")
        
        weight = None
        while True:
            weightLbs = input("Please enter your weight in pounds (optional): ")
            
            # if the user does not enter their weight, exit the loop
            if not weightLbs:
                break
            try:
                weight = float(weightLbs)

                if weight < 0 or weight > 1000:
                    print("You have entered an invalid weight. It must be positive and under 1000 lbs.")
                else:
                    break
            # if we can't convert the entered weight to a float   
            except ValueError:
                print("You have entered an invalid weight. It must be a number.")
        
        bodyFatPercentage = None
        while True:
            bodyFat = input("Please enter your body fat percentage (optional): ")
            
            # if the user does not enter their bodyFat, exit the loop
            if not bodyFat:
                break
            try:
                bodyFatPercentage = float(bodyFat)

                if bodyFatPercentage < 3 or bodyFatPercentage > 85:
                    print("You have entered an invalid body fat percentage. It must be between 3 and 85.")
                else:
                    break
            # if we can't convert the entered bodyFat to a float   
            except ValueError:
                print("You have entered an invalid weight. It must be a number.")

        try:
            cursor = connection.cursor()
            
            cursor.execute("""
                INSERT INTO Member (fName, lName, email, password, dateOfBirth, phoneNumber, weightLbs, bodyFatPercentage)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (fName, lName, email, password, dateOfBirth, phoneNumber, weight, bodyFatPercentage))
            connection.commit()
            
            print("Your account has been registered!")
        except psycopg2.Error as err:
            print("Error while INSERT INTO the database:", err)
        finally:
            cursor.close()
        

    #------------------------------------------------------------------------------------------------------------------
    # Defining the loginUser function which takes in an email, password, and account type and tries to log the user in.
    #------------------------------------------------------------------------------------------------------------------
    def loginUser(email, password, accountType):
        try:
            cursor = connection.cursor()
            
            # If a member is trying to log in
            if accountType == 1: 
                cursor.execute("SELECT * FROM Member WHERE LOWER(email) = LOWER(%s) AND password = %s", (email, password))
                member = cursor.fetchone()

                if member:
                    return member
                else:
                    print("You have entered an invalid email or password.")
                    return None
            
            # If a Trainer is trying to log in
            elif accountType == 2:
                cursor.execute("SELECT * FROM PersonalTrainer WHERE LOWER(email) = LOWER(%s) AND password = %s", (email, password))
                trainer = cursor.fetchone()
                if trainer:
                    print(f"{trainer[1]} {trainer[2]} successfully logged in. Welcome!")
                    return trainer
                else:
                    print("You have entered an invalid email or password.")
                    return None

            # If a staff is trying to log in
            elif accountType == 3:
                cursor.execute("SELECT * FROM AdministrativeStaff WHERE LOWER(email) = LOWER(%s) AND password = %s", (email, password))
                staff = cursor.fetchone()
                if staff:
                    print(f"{staff[1]} {staff[2]} successfully logged in. Welcome!")
                    return staff
                else:
                    print("You have entered an invalid email or password.")
                    return None
            else:
                print("You have entered an invalid account type.")
                return None
        
        except psycopg2.Error as err:
            print("Error while querying the database:", err)
        
        finally:
            cursor.close()

    
    #----------------------------------------------------------------------
    # Defining a helper function to update a member's personal information.
    #----------------------------------------------------------------------
    def updatePersonalInformation(userId):
        try:
            cursor = connection.cursor()
        
            print("\nWhat would you like to update?")
            print("1. First name")
            print("2. Last name")
            print("3. Email")
            print("4. Password")
            print("5. Phone Number")

            personalInfoUpdateChoice = input("Enter your choice (1, 2, 3, 4, or 5). Or anything else to cancel: ")

            if personalInfoUpdateChoice in ['1', '2', '3', '4', '5']:
                if personalInfoUpdateChoice == '1':
                    newFName = input("Enter your new first name: ")
                    cursor.execute("UPDATE Member SET fName = %s WHERE userId = %s", (newFName, userId))
                
                elif personalInfoUpdateChoice == '2':
                    newLName = input("Enter your new last name: ")
                    cursor.execute("UPDATE Member SET lName = %s WHERE userId = %s", (newLName, userId))
                
                elif personalInfoUpdateChoice == '3':
                    while True:
                        newEmail = input("Please enter your new email address: ")

                        # Determining if the email address is an actual email address
                        if re.match(r'^[\w\.-]+@([\w-]+\.)+[\w-]{2,4}$', newEmail):
                            break
                        else:
                            print("You have entered an invalid email. Please try again")
                    
                    cursor.execute("UPDATE Member SET email = %s WHERE userId = %s", (newEmail, userId))
                
                elif personalInfoUpdateChoice == '4':
                    while True:
                        newPassword = input("Please enter your password (min 8 characters, including 1 letter and 1 number): ")

                        # Determining if the password meets the required criteria
                        if len(newPassword) >= 8 and any(c.isalpha() for c in newPassword) and any(c.isdigit() for c in newPassword):
                            break
                        else:
                            print("You have entered an invalid password. Please review the criteria and try again.")
                    
                    cursor.execute("UPDATE Member SET password = %s WHERE userId = %s", (newPassword, userId))
                
                elif personalInfoUpdateChoice == '5':
                    while True:
                        newPhoneNumber = input("Please enter your phone number in the format (###) ###-####: ")
                        
                        if re.match(r'^\(\d{3}\) \d{3}-\d{4}$', newPhoneNumber):
                            break
                        else:
                            print("You have entered an invalid phone number. Please use the format (###) ###-#### where # is a digit.")
                    
                    cursor.execute("UPDATE Member SET phoneNumber = %s WHERE userId = %s", (newPhoneNumber, userId))

                connection.commit()
                print("Personal information updated successfully.")
            else:
                print("Update operation canceled.")

        except psycopg2.Error as err:
            print("Error while updating personal information:", err)

        finally:
            cursor.close()

    
    #----------------------------------------------------------------
    # Defining a helper function to update a member's health metrics.
    #----------------------------------------------------------------
    def updateHealthMetrics(userId):
        try:
            cursor = connection.cursor()
        
            print("\nWhat would you like to update?")
            print("1. Weight (in lbs)")
            print("2. Body Fat Percentage")

            healthMetricsUpdateChoice = input("Enter your choice (1 or 2). Or anything else to cancel: ")

            if healthMetricsUpdateChoice in ['1', '2']:                
                if healthMetricsUpdateChoice == '1':
                    weight = None
                    while True:
                        weightLbs = input("Please enter your weight in pounds (optional): ")
                        
                        # if the user does not enter their weight, exit the loop
                        if not weightLbs:
                            break
                        try:
                            weight = float(weightLbs)

                            if weight < 0 or weight > 1000:
                                print("You have entered an invalid weight. It must be positive and under 1000 lbs.")
                            else:
                                break
                        # if we can't convert the entered weight to a float   
                        except ValueError:
                            print("You have entered an invalid weight. It must be a number.")
                    
                    cursor.execute("UPDATE Member SET weightLbs = %s WHERE userId = %s", (weight, userId))
                
                elif healthMetricsUpdateChoice == '2':
                    bodyFatPercentage = None
                    while True:
                        bodyFat = input("Please enter your new body fat percentage (optional): ")
                        
                        # if the user does not enter their bodyFat, exit the loop
                        if not bodyFat:
                            break
                        try:
                            bodyFatPercentage = float(bodyFat)

                            if bodyFatPercentage < 3 or bodyFatPercentage > 85:
                                print("You have entered an invalid body fat percentage. It must be between 3 and 85.")
                            else:
                                break
                        # if we can't convert the entered bodyFat to a float   
                        except ValueError:
                            print("You have entered an invalid weight. It must be a number.")
                    
                    cursor.execute("UPDATE Member SET bodyFatPercentage = %s WHERE userId = %s", (bodyFatPercentage, userId))

                connection.commit()
                print("Health Metric updated successfully.")
            else:
                print("Update operation canceled.")

        except psycopg2.Error as err:
            print("Error while updating personal information:", err)

        finally:
            cursor.close()

    #------------------------------------------------------------
    # Defining a helper function to get a member's fitness goals.
    #------------------------------------------------------------
    def displayFitnessGoals(userId):
        try:
            cursor = connection.cursor()

            # Selecting that user's fitness goals (specifically the id, name, description, and the achievement date)
            cursor.execute("""
                SELECT achievementId, achievementName, achievementDescription, dateAchieved 
                FROM Achievement 
                WHERE userId = %s
            """, (userId,))

            fitnessGoals = cursor.fetchall()

            for goal in fitnessGoals:
                achievementId, achievementName, achievementDescription, dateAchieved = goal
                
                # Check if dateAchieved is NULL and if so, display its information and state that it has not been achieved
                if dateAchieved is None:
                    print(f"Achievement #{achievementId}")
                    print(f"Achievement: {achievementName}")
                    print(f"Description: {achievementDescription}")
                    print("Goal has not been achieved yet\n")
                
                # if the goal has been achieved, display its information along with the achievement date
                else:
                    print(f"Achievement: {achievementName}")
                    print(f"Description: {achievementDescription}")
                    print(f"Achieved on: {dateAchieved}\n")
        
        except psycopg2.Error as err:
            print("Error while querying the database:", err)
        
        finally:
            cursor.close()

    #---------------------------------------------------------------
    # Defining a helper function to add a fitness goal for a member.
    #---------------------------------------------------------------
    def addFitnessGoal(userId):
        try:
            cursor = connection.cursor()
            
            # Prompt user for achievement details
            achievementName = input("Enter achievement name: ")
            achievementDescription = input("Enter achievement description (optional): ")

            achievementDescription = achievementDescription if achievementDescription != '' else None
            # Insert the new achievement into the database
            cursor.execute("""
                INSERT INTO Achievement (userId, achievementName, achievementDescription)
                VALUES (%s, %s, %s)
            """, (userId, achievementName, achievementDescription))
            
            connection.commit()
            print("Achievement added to the database!\n")
            displayFitnessGoals(userId)
            
        except psycopg2.Error as err:
            print("Error while adding the achievement:", err)
        
        finally:
            cursor.close()
    
    #------------------------------------------------------------------
    # Defining a helper function to update a fitness goal for a member.
    #------------------------------------------------------------------
    def markGoalAchieved(userId, achievementId):
        try:
            cursor = connection.cursor()
            
            # Check if there's a goal with a matching userId and achievementId
            cursor.execute("SELECT * FROM Achievement WHERE userId = %s AND achievementId = %s", (userId, achievementId))
            goal = cursor.fetchone()

            # If the goal exists
            if goal:
                # Check if the goal has already been achieved
                if goal[4] is not None:
                    print("You've already achieved this goal!")
                # If the goal is not achieved, mark it as achieved by setting dateAchieved to now
                else:
                    # Update the goal to mark it as achieved
                    cursor.execute("UPDATE Achievement SET dateAchieved = %s WHERE userId = %s AND achievementId = %s", (datetime.now(), userId, achievementId))
                    connection.commit()
                    print("This goal has successfully been marked as achieved!")
                    displayFitnessGoals(userId)
            else:
                print("No matching goal found.")
            
        except psycopg2.Error as err:
            print("Error while adding the achievement:", err)
        
        finally:
            cursor.close()

    #-----------------------------------------------------------------------
    # Defining a helper function to get a member's fitness health statistics
    #-----------------------------------------------------------------------
    def displayHealthStatistics(userId):
        try:
            cursor = connection.cursor()

            # Selecting that user's health statistics (weight and body fat percentage)
            cursor.execute("SELECT weightLbs, bodyFatPercentage FROM Member WHERE userId = %s;", (userId,))

            
            healthStats = cursor.fetchone()
            weight, bodyFatPercentage = healthStats
            
            # displaying the health stats
            print("Weight: not provided") if weight is None else print(f"Weight: {weight} lbs")
            print("Body Fat Percentage: not provided\n") if bodyFatPercentage is None else print(f"Body Fat Percentage: {bodyFatPercentage}%\n")
    
        except psycopg2.Error as err:
            print("Error while querying the database:", err)
        
        finally:
            cursor.close()

    #----------------------------------------------------------------------------------------------------------------------------
    # Defining a helper function to get a member's fitness achievements. Assuming an achievement is just an achieved fitness goal
    #----------------------------------------------------------------------------------------------------------------------------
    def displayFitnessAchievements(userId):
        try:
            cursor = connection.cursor()

            # Selecting that user's fitness achievements (specifically the name, description, and the achievement date)
            cursor.execute("""
                SELECT achievementName, achievementDescription, dateAchieved 
                FROM Achievement 
                WHERE userId = %s AND dateAchieved IS NOT NULL
            """, (userId,))

            fitnessAchievements = cursor.fetchall()
            if not fitnessAchievements:
                print("You haven't achieved your goals yet. Keep working at it!\n")
            else:
                for achievement in fitnessAchievements:
                    achievementName, achievementDescription, dateAchieved = achievement

                    # display the achievement's information along with the achievement date
                    print(f"Achievement: {achievementName}")
                    print(f"Description: {achievementDescription}")
                    print(f"Achieved on: {dateAchieved}\n")
    
        except psycopg2.Error as err:
            print("Error while querying the database:", err)
        
        finally:
            cursor.close()

    #----------------------------------------------------------------
    # Defining a helper function to get a member's exercise routines.
    #----------------------------------------------------------------
    def displayExerciseRoutines(userId):
        try:
            cursor = connection.cursor()
            
            # Find routines associated with the specified userId
            cursor.execute("""
                SELECT routineId, routineName, routineDescription 
                FROM Routine 
                WHERE userId = %s
            """, (userId,))
            
            routines = cursor.fetchall()
            
            if not routines:
                print("You currently have no exercise routines.\n")
                return
            
            # For each routine, display the name and description
            for routine in routines:
                print(f"Routine Name: {routine[1]}")
                print(f"Routine Description: {routine[2]}")
                
                # Getting the exercises and sets of that exercise associated with each routine. Ordering by rea.routineExerciseId to ensure exercises are displayed in the right order
                cursor.execute("""
                    SELECT e.exerciseName, rea.numSets 
                    FROM RoutineExerciseAssignment rea
                    JOIN Exercise e ON rea.exerciseId = e.exerciseId
                    WHERE rea.routineId = %s
                    ORDER BY rea.routineExerciseId
                """, (routine[0],))
                exercises = cursor.fetchall()
                
                # If there are no exercises for that routine, telling the user
                if not exercises:
                    print("No exercises found for this routine.")
                # Otherwise displaying the exercises for that routine as well as how many sets there are
                else:
                    for exercise in exercises:
                        print(f"{exercise[1]} sets of {exercise[0]}")
                print()
            
        except psycopg2.Error as err:
            print("Error while querying the database:", err)
        finally:
            cursor.close()
    
    #--------------------------------------------------------------------------
    # Defining a helper function to let a member create a new exercise routine.
    #--------------------------------------------------------------------------
    def createRoutine(userId):
        try:
            cursor = connection.cursor()
            
            # Getting the routine name and routine description via user input
            routineName = input("Enter routine name: ")
            routineDescription = input("Enter routine description: ")

            # Inserting a new routine with the provideed info and the userId
            cursor.execute("INSERT INTO Routine (routineName, userId, routineDescription) VALUES (%s, %s, %s) RETURNING routineId;", (routineName, userId, routineDescription))
            routineId = cursor.fetchone()[0] 

            # Selecting all the exercises in the DB and displaying them along with their ID number
            cursor.execute("SELECT exerciseId, exerciseName, exerciseDescription FROM Exercise;")
            exercises = cursor.fetchall()

            print("Available Exercises:")
            for exercise in exercises:
                print(f"{exercise[0]} - {exercise[1]}")
            
            # Letting the user choose which exercises they would like to add to their routine, as well as the number of sets for the exercise
            routineExercises = []
            while True:
                try:
                    # Determining if the user entered a valid exercise or "done"
                    chosenExercise = input("Please enter the exercise id of the exercise you'd like to add (or 'done' to finish): ")
                    if chosenExercise.lower() == 'done':
                        break
                    elif not chosenExercise.isdigit():
                        print("The exercise ID you have entered is invalid. Please try again.")
                        continue
                    elif int(chosenExercise) not in [exercise[0] for exercise in exercises]:
                        print("The exercise ID you have entered is invalid. Please try again.")
                        continue
                    else:
                        numSets = input("Enter number of sets: ")
                        routineExercises.append((int(chosenExercise), int(numSets)))
                
                except ValueError:
                    print("Make sure to enter integers unless you are done adding exercises.")
            
            # Inserting the exercises that the user selected into RoutineExerciseAssignment table
            for chosenExercise, numSets in routineExercises:
                cursor.execute("INSERT INTO RoutineExerciseAssignment (routineId, exerciseId, numSets) VALUES (%s, %s, %s);", (routineId, chosenExercise, numSets))
            
            connection.commit()
            print("Routine created successfully!")

        except psycopg2.Error as err:
            print("Error creating the routine:", err)
        
        finally:
            cursor.close()

    #------------------------------------------------------------------------------------------------------------
    # Defining the profileManagement function which lets the user manage their profile as specified in the specs.
    #------------------------------------------------------------------------------------------------------------
    def profileManagement(userId):
        print("\nPROFILE MANAGEMENT:")
        print("What would you like to do?")
        print("1. Update Personal Information")
        print("2. Update Fitness Goals")
        print("3. Update Health Metrics")
        
        choice1 = input("Enter your choice (1, 2, or 3). Or anything else to cancel: ")
        if choice1.isdigit():
            choice1 = int(choice1)
        else:
            return

        if choice1 == 1:
            updatePersonalInformation(userId)

        elif choice1 == 2:
            print("The following are your fitness goals:")
            displayFitnessGoals(userId)
            goalChoice = input("Enter Y to add a goal, the fitness goal's ID to mark it as achieved, or anything else to exit: ")
            if goalChoice.upper() == 'Y':
                addFitnessGoal(userId)
            if goalChoice.isdigit():
                markGoalAchieved(userId, int(goalChoice))
        
        elif choice1 == 3:
            updateHealthMetrics(userId)

    #------------------------------------------------------------------------------------------------------
    # Defining the displayDashboard function which displays the user's dashboard as specified in the specs.
    #------------------------------------------------------------------------------------------------------
    def displayDashboard(userId):
        print("Your health statistics: ")
        displayHealthStatistics(userId)
        print("Your fitness achievements: ")
        displayFitnessAchievements(userId)
        print("Your Exercise Routines: ")
        displayExerciseRoutines(userId)

        routineAdditionChoice = input("Enter Y to create a new exercise routine or anything else to exit: ")
        if routineAdditionChoice.upper() == 'Y':
            createRoutine(userId)

    # --------------------------------------------------------------------------------------
    # Defining a displayAllClasses function which the staff members can use to view classes.
    #---------------------------------------------------------------------------------------
    def displayAllClasses():
        try:
            cursor = connection.cursor()

            # Getting all the classes from the database and displaying them
            cursor.execute("SELECT classId, className, trainerId, classDate, startTime, endTime FROM Class")
            classes = cursor.fetchall()

            if not classes:
                print("No classes in the database.")
            else:
                print("The database has the following classes:")
                for classInDb in classes:
                    print(f"\t Class #{classInDb[0]} - {classInDb[1]}: Taught by trainer #{classInDb[2]} taught on {classInDb[3]} at {classInDb[4]} to {classInDb[5]}")

        except psycopg2.Error as err:
            print("Error while displaying classes:", err)
        
        finally:
            cursor.close()

    #---------------------------------------------------------------------------------------------------------
    # Defining a displayRegisteredClasses function which lets us display all classes a user is registered in
    #---------------------------------------------------------------------------------------------------------
    def displayRegisteredClasses(userId):
        try:
            cursor = connection.cursor()

            # Get classes the user is registered in.
            cursor.execute("""
                SELECT Class.classId, Class.className, Class.classDate, Class.startTime, Class.endTime
                FROM MemberTakesClass JOIN Class ON MemberTakesClass.classId = Class.classId
                WHERE MemberTakesClass.userId = %s
                ORDER BY Class.classDate ASC
            """, (userId,))
            registeredClasses = cursor.fetchall()
            
            if not registeredClasses:
                print("You are not currently registered in any class")
                return
            

            print("You are registered in the following classes:")
            for registeredClass in registeredClasses:
                print(f"\tClass #{registeredClass[0]} - Class Name: {registeredClass[1]} on {registeredClass[2]} at {registeredClass[3]} to {registeredClass[4]}")
        
        except psycopg2.Error as err:
            print("Error while displaying registered classes:", err)
        finally:
            cursor.close()

    #---------------------------------------------------------------------------------------------------------
    # Defining a displayPtSessions function which lets us display all PT sessions a user is registered in
    #---------------------------------------------------------------------------------------------------------
    def displayPtSessions(userId):
        try:
            cursor = connection.cursor()

            # Get PT sessions the user is registered in.
            cursor.execute("""
                SELECT PersonalTrainingSession.sessionId, PersonalTrainer.fName, PersonalTrainer.lName, PersonalTrainingSession.sessionDate, PersonalTrainingSession.startTime, PersonalTrainingSession.endTime
                FROM PersonalTrainingSession JOIN PersonalTrainer ON PersonalTrainingSession.trainerId = PersonalTrainer.trainerId
                WHERE PersonalTrainingSession.userId = %s
                ORDER BY PersonalTrainingSession.sessionDate ASC
            """, (userId,))
            registeredPtSessions = cursor.fetchall()
            
            if not registeredPtSessions:
                print("You are not currently registered in any PT sessions")
                return
            

            print("You are registered in the following PT sessions:")
            for session in registeredPtSessions:
                print(f"\tSession #{session[0]} with Trainer {session[1]} {session[2]} on {session[3]} at {session[4]} to {session[5]}")
        
        except psycopg2.Error as err:
            print("Error while displaying registered PT sessions:", err)
        finally:
            cursor.close()


    #------------------------------------------------------------------------------------------
    # Defining a userRegisterClass function which lets the user register themselves for a class
    #------------------------------------------------------------------------------------------
    def userRegisterClass(userId):
        try:
            cursor = connection.cursor()

            # show the user all the classes for them to choose one to join
            displayAllClasses()
            classId = input("Enter the class ID that you would like to join: ")

            # determining if the user entered a valid classId
            cursor.execute("SELECT * FROM Class WHERE classId = %s", (classId,))
            classFromDb = cursor.fetchone()
            
            if not classFromDb:
                print("Invalid class ID. Class not found.")
                return

            # Seeing if the user is unavailable at the time of the class
            if not checkUserAvailability(userId, classFromDb[3], classFromDb[4], classFromDb[5]):
                print("You are already registered for a class at that time.")
                return

            # Adding the user to the MemberTakesClass table for the class they'd like to join
            cursor.execute("INSERT INTO MemberTakesClass (userId, classId) VALUES (%s, %s)", (userId, classId))
            connection.commit()

            print(f"You have successfully joined class #{classId}.")
            displayRegisteredClasses(userId)
        except psycopg2.Error as err:
            print("Error while registering for the class:", err)
        finally:
            cursor.close()
    
    #---------------------------------------------------------------------------------------------------
    # Defining a userRegisterPtSession function which lets the user register themselves for a PT Session
    #---------------------------------------------------------------------------------------------------
    def userRegisterPtSession(userId):
        try:
            cursor = connection.cursor()

            while True:
                sessionDate = input("Please enter the date that you'd like the session to be on in the format YYYY-MM-DD: ")

                # Determining if the sessionDate meets the required format and its a valid sessionDate
                if re.match(r'^\d{4}-\d{2}-\d{2}$', sessionDate):
                    if isValidDate(sessionDate, 2022):
                        break
                    else:
                        print("You have entered an invalid date. Please enter a valid date after January 1, 2022 (when the gym was opened).")
                else:
                    print("You have entered an invalid date. Please use the format YYYY-MM-DD (ex. 2023-04-15).")
            
            # Letting the user set the start time for the session
            while True:
                startTime = input("Please enter the start time of the new session in 24 hr format (HH:MM): ")
                if re.match(r"^(?:[0-1]?[0-9]|2[0-3]):[0-5][0-9]$", startTime):
                    break
                else:
                    print("You have entered an invalid start time. Please use the format HH:MM format (ex. 9:30 or 17:30).")

            # Letting the user set the end time for the session
            while True:
                endTime = input("Please enter the end time of the new session in 24 hr format (HH:MM): ")
                if re.match(r"^(?:[0-1]?[0-9]|2[0-3]):[0-5][0-9]$", endTime):
                    # Making sure that the endTime is after the startTime before breaking
                    startDateTime = datetime.strptime(startTime, "%H:%M")
                    endDateTime = datetime.strptime(endTime, "%H:%M")
                    
                    if endDateTime > startDateTime:
                        break
                    else:
                        print("You have entered an invalid end time. Please make sure the end time is after start time.")
                else:
                    print("You have entered an invalid end time. Please use the format HH:MM format (ex. 9:30 or 17:30).")
            
            # Checking if the user is available during the requested session time
            if not checkUserAvailability(userId, sessionDate, startTime, endTime):
                print("You already have a booking in this timeframe. Please choose another time.")
                return
            
            # Check what trainers are available for the requested session time
            cursor.execute("SELECT trainerId, fName, lName FROM PersonalTrainer")
            trainers = cursor.fetchall()

            availableTrainers = []
            for trainer in trainers:
                if checkTrainerAvailability(trainer[0], sessionDate, startTime, endTime):
                    availableTrainers.append(trainer)
            
            if not availableTrainers:
                print("No trainers are available at the requested time.")
                return

            # display the available trainers and let the user choose a trainer. Then make sure the trainer they chose is valid, and if so, create a PT session in the DB
            print("Available Trainers during that session time:")
            for trainer in availableTrainers:
                print(f"\tTrainer #{trainer[0]} - {trainer[1]} {trainer[2]}")
            
            trainerId = input("Enter the ID of the trainer you would like to choose for your session: ")

            validTrainerIds = [str(trainer[0]) for trainer in availableTrainers]
            if trainerId not in validTrainerIds:
                print("Invalid trainer ID. Please make sure to choose a valid trainer ID for the PT session.")
                return

            cursor.execute("INSERT INTO PersonalTrainingSession (userId, trainerId, sessionDate, startTime, endTime) VALUES (%s, %s, %s, %s, %s)", (userId, trainerId, sessionDate, startTime, endTime))
            connection.commit()

            print(f"You have been registered for the session with {trainer[1]} {trainer[2]} on {sessionDate} from {startTime} to {endTime}")
        except psycopg2.Error as err:
            print("Error while registering for PT session:", err)
        finally:
            cursor.close()

    #-----------------------------------------------------------------------------------------------
    # Defining a userDeregisterClass function which lets the user deregister themselves from a class
    #-----------------------------------------------------------------------------------------------
    def userDeregisterClass(userId):
        try:
            cursor = connection.cursor()

            # show the user all the classes that they are registered in
            displayRegisteredClasses(userId)

            classId = input("Enter the class ID that you would like to deregister from: ")

            # determining if the user entered a valid classId
            cursor.execute("SELECT * FROM MemberTakesClass WHERE userId = %s AND classId = %s", (userId, classId))
            memberTakesClass = cursor.fetchone()
            
            # if the user entered an invalid class ID, telling them
            if not memberTakesClass:
                print("Invalid class ID. Class not found.")
                return

            # Otherwise removing the entry from MemberTakesClass
            cursor.execute("DELETE FROM MemberTakesClass WHERE userId = %s AND classId = %s", (userId, classId))
            connection.commit()
            
            print("Successfully unregistered from the class.")
            displayRegisteredClasses(userId)

        except psycopg2.Error as err:
            print("Error while deregistering from the class:", err)
        finally:
            cursor.close()

    #------------------------------------------------------------------------------------------------------
    # Defining a userDeregisterPtSession function which lets the user deregister themselves from a ptSession
    #------------------------------------------------------------------------------------------------------
    def userDeregisterPtSession(userId):
        try:
            cursor = connection.cursor()

            # show the user all the PT sessions that they are registered in
            displayPtSessions(userId)

            sessionId = input("Enter the session ID that you would like to deregister from: ")

            # determining if the user entered a valid sessionId
            cursor.execute("SELECT * FROM PersonalTrainingSession WHERE userId = %s AND sessionId = %s", (userId, sessionId))
            session = cursor.fetchone()

            # if the user entered an invalid class ID, telling them
            if not session  :
                print("Invalid Personal Training Session ID. Session not found.")
                return
            
            # Otherwise removing the entry from PersonalTrainingSession
            cursor.execute("DELETE FROM PersonalTrainingSession WHERE userId = %s AND sessionId = %s", (userId, sessionId))
            connection.commit()
            
            print("Successfully unregistered from the PT session.")
            displayPtSessions(userId)

        except psycopg2.Error as err:
            print("Error while deregistering from the class:", err)
        finally:
            cursor.close()






    #----------------------------------------------------------------------------------------------------------------------------
    # Defining the userScheduleManagement function which lets the user register/remove themselves from PT sessions and/or classes
    #----------------------------------------------------------------------------------------------------------------------------
    def userScheduleManagement(userId):
        displayRegisteredClasses(userId)
        displayPtSessions(userId)
        print("Choose what you would like to do (select the corresponding number): ")
        print("1. Register for a class")
        print("2. Register for a PT session")
        print("3. Unregister from a class")
        print("4. Unregister from a PT session")
        
        while True:
            try:
                userScheduleChoice = int(input("Enter your choice (1, 2, 3, or 4): "))
            except ValueError:
                print("Make sure to enter an integer. Please try again.\n")
                continue

            if userScheduleChoice < 1 or userScheduleChoice > 4:
                print("You have chosen an invalid number. Please try again.\n")
            else:
                break
        
        if userScheduleChoice == 1:
            userRegisterClass(userId)
        elif userScheduleChoice == 2:
            userRegisterPtSession(userId)
        elif userScheduleChoice == 3:
            userDeregisterClass(userId)
        elif userScheduleChoice == 4:
            userDeregisterPtSession(userId)

        

    # ------------------------------------------------------------------------------------------------------------------
    # Defining the displayAvailability function which the trainer can use to view their availability for a desired date.
    # ------------------------------------------------------------------------------------------------------------------
    def displayAvailability(trainerId, date):
        try:
            cursor = connection.cursor()

            # Query the database to fetch availability for the specified trainer and date
            cursor.execute("""
                SELECT availibilityId, startTime, endTime 
                FROM TrainerAvailability 
                WHERE trainerId = %s AND availabilityDate = %s
                ORDER BY startTime
            """, (trainerId, date))
            
            availabilities = cursor.fetchall()

            if not availabilities:
                print("No availability found for the specified date.")
            else:
                for availability in availabilities:
                    print(f"Availability #{availability[0]} - Start Time: {availability[1]}, End Time: {availability[2]}")
            print()
            
        except psycopg2.Error as err:
            print("Error while fetching availability:", err)
        finally:
            cursor.close()

    # -------------------------------------------------------------------------------------------------------------------------
    # Defining the setAvailability function which the trainer can use to update their availability for a desired date and time.
    # -------------------------------------------------------------------------------------------------------------------------
    def setAvailability(trainerId):
        try:
            cursor = connection.cursor()

            # Letting the user set the availabilityDate
            while True:
                availabilityDate = input("Please enter the date who's availability you'd like to change in the format YYYY-MM-DD: ")

                # Determining if the availabilityDate meets the required format and its a valid date
                if re.match(r'^\d{4}-\d{2}-\d{2}$', availabilityDate):
                    if isValidDate(availabilityDate, 2022):
                        print("The following is your current availability for that date: ")
                        displayAvailability(trainerId, availabilityDate)

                        break
                    else:
                        print("You have entered an invalid date. Please enter a valid date after January 1, 2022 (when the gym was opened).")
                else:
                    print("You have entered an invalid date. Please use the format YYYY-MM-DD (ex. 2023-04-15).")
            
            # Asking the user if they'd like to set a new availability or remove an availability


            # Letting the user set the start time for the availabilityDate
            while True:
                startTime = input("Please enter the start time of your availability in 24 hr format (HH:MM): ")
                if re.match(r"^(?:[0-1]?[0-9]|2[0-3]):[0-5][0-9]$", startTime):
                    break
                else:
                    print("You have entered an invalid start time. Please use the format HH:MM format (ex. 9:30 or 17:30).")

            # Letting the user set the end time for the availabilityDate
            while True:
                endTime = input("Please enter the end time of your availability in 24 hr format (HH:MM): ")
                if re.match(r"^(?:[0-1]?[0-9]|2[0-3]):[0-5][0-9]$", endTime):
                    # Making sure that the endTime is after the startTime before breaking
                    startDateTime = datetime.strptime(startTime, "%H:%M")
                    endDateTime = datetime.strptime(endTime, "%H:%M")
                    
                    if endDateTime > startDateTime:
                        # Making sure the availability that the user is trying to set is not overlapping with an existing availability for this trainer. And if it is, just returning out of the function to give the user the opportunity to reconsider their availability.
                        cursor.execute("""
                            SELECT COUNT(*) 
                            FROM TrainerAvailability 
                            WHERE trainerId = %s 
                            AND availabilityDate = %s 
                            AND ((%s BETWEEN startTime AND endTime) OR (%s BETWEEN startTime AND endTime) OR (%s < startTime AND %s > endTime))
                        """, (trainerId, availabilityDate, startTime, endTime, startTime, endTime))
                        
                        if cursor.fetchone()[0] == 0:
                            cursor.execute("INSERT INTO TrainerAvailability (trainerId, availabilityDate, startTime, endTime) VALUES (%s, %s, %s, %s);", (trainerId, availabilityDate, startTime, endTime))
                            connection.commit()
                            print("Availability for", availabilityDate, "has been set!")
                            return
                        else:
                            print("Your availability overlaps with an existing availability that you've already set. Please choose a different time range.")
                            return
                    else:
                        print("You have entered an invalid end time. Please make sure the end time is after start time.")
                else:
                    print("You have entered an invalid end time. Please use the format HH:MM format (ex. 9:30 or 17:30).")

        except psycopg2.Error as err:
            print("Error while setting availability:", err)
        finally:
            cursor.close()


    # --------------------------------------------------------------------------------------------------------------------------
    # Defining the searchMemberProfile function which the trainer can use to display a user's profile as specified in the specs.
    #---------------------------------------------------------------------------------------------------------------------------
    def searchMemberProfile(fName, lName):
        try:
            cursor = connection.cursor()

            # Finding the members that meet the search criteria (matching first name and last name)
            cursor.execute("""
                SELECT userId, fName, lName, email, dateOfBirth, phoneNumber, weightLbs, bodyFatPercentage
                FROM Member 
                WHERE LOWER(fName) = LOWER(%s) AND LOWER(lName) = LOWER(%s);
            """, (fName, lName))
            members = cursor.fetchall()

            # If no matching members are found, telling the user
            if not members:
                print(f"\nThere are no members named {fName} {lName}")
                return

            # Otherwise looping through all the members with that name and displaying their personal information, health statistics, and achievements
            for member in members:
                print("\nMember Personal Information:")
                print("User ID:", member[0])
                print("First name:", member[1])
                print("Last name:", member[2])
                print("Email:", member[3])
                print("Date of Birth:", member[4])
                print("Phone Number:", member[5])

                print("\nMember Health Statistics: ")
                print("Weight: not provided") if member[6] is None else print(f"Weight: {member[6]} lbs")
                print("Body Fat Percentage: not provided\n") if member[7] is None else print(f"Body Fat Percentage: {member[7]}%\n")

                # Getting that member's achievements
                cursor.execute("""
                    SELECT achievementName, achievementDescription, dateAchieved
                    FROM Achievement
                    WHERE userId = %s;
                """, (member[0],))
                achievements = cursor.fetchall()

                if not achievements:
                    print(f"{fName} {lName} has not yet achieved their goals.\n")
                else:
                    for achievement in achievements:
                        achievementName, achievementDescription, dateAchieved = achievement

                        # display the achievement's information along with the achievement date
                        print(f"Achievement: {achievementName}")
                        print(f"Description: {achievementDescription}")
                        print(f"Achieved on: {dateAchieved}\n")
                
                print("------------------------------------------------------------------")

        except psycopg2.Error as err:
            print("Error while querying the database:", err)

        finally:
            cursor.close()
    

    # -----------------------------------------------------------------------------------------------------------------------
    # Defining the displayRoomBookings function which the user can use to view the existing room bookings for a desired date.
    # -----------------------------------------------------------------------------------------------------------------------
    def displayRoomBookings(roomNumber, date):
        try:
            cursor = connection.cursor()

            # Getting the associated room name
            cursor.execute("SELECT roomName FROM Room WHERE roomNumber = %s", (roomNumber,))
            roomName = cursor.fetchone()[0]

            # Query the database to fetch room bookings for the specified room and date
            cursor.execute("""
                SELECT roomBookingId, startTime, endTime
                FROM RoomBookings
                WHERE roomNumber = %s AND bookingDate = %s
                ORDER BY startTime
            """, (roomNumber, date))
            bookings = cursor.fetchall()

            if not bookings:
                print(f"No bookings found for {roomName} on the specified date.")
            else:
                print(f"Bookings found for {roomName} on the specified date:")
                for booking in bookings:
                    print(f"\tRoom Booking #{booking[0]} - Start Time: {booking[1]}, End Time: {booking[2]}")
            print()
            
        except psycopg2.Error as err:
            print("Error while fetching availability:", err)
        finally:
            cursor.close()
        
    # ----------------------------------------------------------------------------------------------------------
    # Defining the manageRoomBookings function which the staff member can use to create or remove room bookings.
    #-----------------------------------------------------------------------------------------------------------
    def manageRoomBookings(staffId):
        try:
            cursor = connection.cursor()

            # Displaying all the rooms to the user
            cursor.execute("SELECT roomNumber, roomName FROM Room")
            rooms = cursor.fetchall()
            print("Rooms:")
            for room in rooms:
                print(f"Room #{room[0]}: {room[1]}")

            print("What would you like to do?")
            print("1. Create a new room booking")
            print("2. Remove an existing room booking")

            choice = input("Enter your choice (1 or 2): ")

            if not(choice == '1' or choice == '2'):
                print("Invalid choice")
                return

            # Getting the room number and booking date and seeing if the room exists and if so, displaying the bookings for that date.
            roomNumber = input("Enter the room number: ")

            while True:
                bookingDate = input("Please enter the date you'd like to manage the room booking for in the format YYYY-MM-DD: ")

                # Determining if the bookingDate meets the required format and its a valid date. If so, checking if the room exists, if it does not, informing the user and returning.
                if re.match(r'^\d{4}-\d{2}-\d{2}$', bookingDate):
                    if isValidDate(bookingDate, 2022):
                        cursor.execute("SELECT roomNumber, roomName FROM Room WHERE roomNumber = %s", (roomNumber,))
                        
                        room = cursor.fetchone()
                        
                        if not room:
                            print("Room not found.")
                            return
                        
                        # displaying the room bookings on that date
                        displayRoomBookings(roomNumber, bookingDate)
                        break
                    else:
                        print("You have entered an invalid date. Please enter a valid date after January 1, 2022 (when the gym was opened).")
                else:
                    print("You have entered an invalid date. Please use the format YYYY-MM-DD (ex. 2023-04-15).")
                
            
            if choice == '1':
                while True:
                    startTime = input("Please enter the start time of the room booking in 24 hr format (HH:MM): ")
                    if re.match(r"^(?:[0-1]?[0-9]|2[0-3]):[0-5][0-9]$", startTime):
                        break
                    else:
                        print("You have entered an invalid start time. Please use the format HH:MM format (ex. 9:30 or 17:30).")

                # Letting the user set the end time for the bookingDate
                while True:
                    endTime = input("Please enter the end time of the room booking in 24 hr format (HH:MM): ")
                    if re.match(r"^(?:[0-1]?[0-9]|2[0-3]):[0-5][0-9]$", endTime):
                        # Making sure that the endTime is after the startTime before breaking
                        startDateTime = datetime.strptime(startTime, "%H:%M")
                        endDateTime = datetime.strptime(endTime, "%H:%M")
                        
                        if endDateTime > startDateTime:
                            # Making sure the room booking that the user is trying to set is not overlapping with an existing room booking for this room. And if it is, just returning out of the function to give the user the opportunity to reconsider the room booking.
                            cursor.execute("""
                                SELECT COUNT(*) 
                                FROM RoomBookings 
                                WHERE roomNumber = %s 
                                AND bookingDate = %s 
                            AND ((%s BETWEEN startTime AND endTime) OR (%s BETWEEN startTime AND endTime) OR (%s < startTime AND %s > endTime))
                            """, (roomNumber, bookingDate, startTime, endTime, startTime, endTime))
                            
                            if cursor.fetchone()[0] == 0:
                                cursor.execute("INSERT INTO RoomBookings (roomNumber, bookingDate, startTime, endTime, bookingStaffId) VALUES (%s, %s, %s, %s, %s);", (roomNumber, bookingDate, startTime, endTime, staffId))
                                connection.commit()
                                print(f"Booking for room #{roomNumber} on {bookingDate} has been set!")
                                displayRoomBookings(roomNumber, bookingDate)

                                return
                            else:
                                print("Your availability overlaps with an existing booking that for this room/date. Please choose a different date.")
                                return
                        else:
                            print("You have entered an invalid end time. Please make sure the end time is after start time.")
                    else:
                        print("You have entered an invalid end time. Please use the format HH:MM format (ex. 9:30 or 17:30).")

            elif choice == '2':
                # Removing an existing room booking
                roomBookingId = input("Enter the room booking ID to remove: ")
                cursor.execute("SELECT roomBookingId FROM RoomBookings WHERE roomBookingId = %s", (roomBookingId,))
                existingBooking = cursor.fetchone()

                if existingBooking:
                    cursor.execute("DELETE FROM RoomBookings WHERE roomBookingId = %s", (roomBookingId,))
                    connection.commit()
                    print(f"Booking with ID {roomBookingId} has been removed.")
                    displayRoomBookings(roomNumber, bookingDate)

                else:
                    print("Room booking does not exist.")
                    return
            
        except psycopg2.Error as err:
            print("Error while managing room bookings:", err)
        finally:
            cursor.close()

    # -------------------------------------------------------------------------------------------------------------------
    # Defining the eqipmentMaintenanceMonitoring function which the staff member can use to manage equipment maintenance.
    #--------------------------------------------------------------------------------------------------------------------
    def equipmentMaintenanceMonitoring():
        try:
            cursor = connection.cursor()

            # Displaying all the equipment to the user
            cursor.execute("SELECT equipmentId, equipmentName, underMaintenance FROM Equipment ORDER BY equipmentId")
            allEquipment = cursor.fetchall()
            print("Equipment:")
            for equipment in allEquipment:
                print(f"Equipment #{equipment[0]}: {equipment[1]} - Currently Under Maintenance") if equipment[2] else print(f"Equipment #{equipment[0]}: {equipment[1]}")

            print("What would you like to do?")
            print("1. Mark an equipment as under maintenance")
            print("2. Mark maintenance as complete for an equipment")

            choice = input("Enter your choice (1 or 2): ")

            if not(choice == '1' or choice == '2'):
                print("Invalid choice")
                return

            # Getting the equipmentId and seeing if the equipment exists and if so, displaying the maintenance history for it.
            equipmentId = input("Enter the equipment id: ")

            cursor.execute("SELECT * FROM Equipment WHERE equipmentId = %s", (equipmentId,))
            equipment = cursor.fetchone()
            if not equipment:
                print(f"No equipment found with ID #{equipmentId}.")
                return
            
            cursor.execute("SELECT maintenanceId, maintenanceCompletionDate FROM EquipmentMaintenance WHERE equipmentId = %s ORDER BY maintenanceCompletionDate DESC NULLS FIRST", (equipmentId,))
            maintenanceHistory = cursor.fetchall() 

            if maintenanceHistory:
                print(f"Maintenance history for Equipment #{equipment[0]} - {equipment[1]}")
                for maintenance in maintenanceHistory:
                    print(f"\tMaintenance ID: {maintenance[0]}, Completion Date: {maintenance[1]}")
            else:
                print(f"No maintenance history for Equipment #{equipment[0]} - {equipment[1]}")
            
            if choice == '1':
                # If the equipment is not already under maintenance, marking the equipment the user provided as under maintenance. Also adding it to the EquipmentMaintenance table
                if not(equipment[2]):
                    cursor.execute("UPDATE Equipment SET underMaintenance = TRUE WHERE equipmentId = %s", (equipmentId,))
                    connection.commit()
                    cursor.execute("INSERT INTO EquipmentMaintenance (equipmentId) VALUES (%s)", (equipmentId,))
                    connection.commit()
                    print(f"Equipment #{equipmentId} has been marked as under maintenance.")
                else:
                    print("Equipment is already under maintenance.")

            elif choice == '2':
                # If the equipment is currently under maintenance, marking the maintenance as complete and updating the equipment maintenance table with a completion date
                if(equipment[2]):
                    cursor.execute("UPDATE Equipment SET underMaintenance = FALSE WHERE equipmentId = %s", (equipmentId,))
                    connection.commit()
                    cursor.execute("UPDATE EquipmentMaintenance SET maintenanceCompletionDate = CURRENT_TIMESTAMP WHERE equipmentId = %s AND maintenanceCompletionDate IS NULL", (equipmentId,))
                    connection.commit()
                    print(f"Maintenance for equipment #{equipmentId} has been marked as complete.")
                else:
                    print("Equipment is not currently under maintenance.")
            
        except psycopg2.Error as err:
            print("Error while managing room bookings:", err)
        finally:
            cursor.close()
    
    # ------------------------------------------------------------------------------------------------------------------------------------
    # Defining the managePayment function which the staff member can use to create a payment, cancel a bill, pay a bill, or refund a bill.
    #-------------------------------------------------------------------------------------------------------------------------------------
    def managePayment():
        try:
            cursor = connection.cursor()
        
            print("What would you like to do? (Select its corresponding number):")
            print("1. Create a new bill")
            print("2. Cancel a bill")
            print("3. Pay a bill")
            print("4. Refund a bill")
            billChoice = input("Enter your choice: ")

            if not(billChoice == '1' or billChoice == '2' or billChoice == '3' or billChoice == '4'):
                print("Invalid choice")
                return
            
            # Create a new bill
            if billChoice == '1':
                # Displaying all members
                cursor.execute("SELECT userId, fName, lName FROM Member")
                members = cursor.fetchall()
                print("All Members:")
                for member in members:
                    print(f"Member #{member[0]} - {member[1]} {member[2]}")

                # Determining what member to bill and checking if they exist
                memberId = input("Enter the ID of the member you'd like to bill: ")
                cursor.execute("SELECT * FROM Member WHERE userId = %s", (memberId,))
                member = cursor.fetchone()

                # If the member is found, determining the payment amount and creating a new entry in the payment table with status Awaiting Payment and statusUpdateDate as now
                if member:
                    while True:
                        try:
                            paymentAmount = float(input("Enter the payment amount ($): "))
                            break
                        except ValueError:
                            print("Invalid input. Please enter a valid number.")
                    
                    cursor.execute("INSERT INTO Payment (memberId, paymentAmount, paymentStatus, statusUpdateDate) VALUES (%s, %s, %s, %s)", (memberId, paymentAmount, 'Awaiting Payment', datetime.now()))
                    connection.commit()
                    print("Bill created successfully.")
                else:
                    print("Invalid member ID. Does not exist.")
            
            # Cancel a bill
            elif billChoice == '2':
                # Display all the bills to the user that are awaiting payment, let them choose the bill that they'd like to cancel.
                cursor.execute("SELECT billNumber, memberId, paymentAmount FROM Payment WHERE paymentStatus = 'Awaiting Payment'")
                bills = cursor.fetchall()

                if not bills:
                    print("There are no bills with the status \"awaiting payment\".")
                    return
                
                print("Bills with status \"awaiting payment\":")
                for bill in bills:
                    print(f"Bill #{bill[0]} for Member #{bill[1]} - Payment Due: ${bill[2]}")
                

                # Verifying that the user entered a valid billNumber
                try:
                    billNumberToCancel = int(input("Enter the bill number to cancel: "))
                    if any(bill[0] == billNumberToCancel for bill in bills):
                        # Cancelling the bill that the user would like to cancel
                        cursor.execute("UPDATE Payment SET paymentStatus = 'Cancelled', statusUpdateDate = CURRENT_TIMESTAMP WHERE billNumber = %s", (billNumberToCancel,))
                        connection.commit()
                    else:
                        print("Invalid bill number. Please enter a valid bill number.")
                except ValueError:
                    print("Invalid bill number. Please make sure to enter an integer.")
            
            # Pay a bill
            elif billChoice == '3':
                # Display all the bills to the user that are awaiting payment, let them choose the bill that they'd like to process the member for right now.
                cursor.execute("SELECT billNumber, memberId, paymentAmount FROM Payment WHERE paymentStatus = 'Awaiting Payment'")
                bills = cursor.fetchall()

                if not bills:
                    print("There are no bills with the status \"awaiting payment\".")
                    return
                
                print("Bills with status \"awaiting payment\":")
                for bill in bills:
                    print(f"Bill #{bill[0]} for Member #{bill[1]} - Payment Due: ${bill[2]}")
                

                # Verifying that the user entered a valid billNumber
                try:
                    billNumberToProcess = int(input("Enter the bill number that is being processed right now: "))
                    if any(bill[0] == billNumberToProcess for bill in bills):
                        # Billing the user for the bill that is being paid
                        print("Bill being paid via integrated payment service")
                        cursor.execute("UPDATE Payment SET paymentStatus = 'Paid', statusUpdateDate = CURRENT_TIMESTAMP WHERE billNumber = %s", (billNumberToProcess,))
                        connection.commit()
                    else:
                        print("Invalid bill number. Please enter a valid bill number.")
                except ValueError:
                    print("Invalid bill number. Please make sure to enter an integer.")

            # Refund a bill
            elif billChoice == '4':
                # Display all the bills to the user that are paid, let them choose the bill that they'd like to refund.
                cursor.execute("SELECT billNumber, memberId, paymentAmount, statusUpdateDate FROM Payment WHERE paymentStatus = 'Paid'")
                bills = cursor.fetchall()

                if not bills:
                    print("There are no bills with the status \"paid\".")
                    return
                
                print("Bills with status \"paid\":")
                for bill in bills:
                    print(f"Bill #{bill[0]} for Member #{bill[1]} - Payment Made: ${bill[2]} on {bill[3]}")
                

                # Verifying that the user entered a valid billNumber
                try:
                    billNumberToRefund = int(input("Enter the bill number that is being refunded right now: "))
                    if any(bill[0] == billNumberToRefund for bill in bills):
                        # Refunding the user for the bill that is being refunded
                        print("User being refunded via the integrated payment service")
                        cursor.execute("UPDATE Payment SET paymentStatus = 'Returned', statusUpdateDate = CURRENT_TIMESTAMP WHERE billNumber = %s", (billNumberToRefund,))
                        connection.commit()
                    else:
                        print("Invalid bill number. Please enter a valid bill number.")
                except ValueError:
                    print("Invalid bill number. Please make sure to enter an integer.")
        
        except psycopg2.Error as err:
            print("Error while processing payment:", err)
        finally:
            cursor.close()

    # ----------------------------------------------------------------------------------------------------------
    # Defining the classScheduleUpdate function which the staff members can use to create and/or delete classes.
    #-----------------------------------------------------------------------------------------------------------
    def classScheduleUpdate():
        try:
            cursor = connection.cursor()

            print("What would you like to do?")
            print("1. Add a class")
            print("2. Remove a class")

            choice = input("Enter your choice (1 or 2): ")
            
            if not(choice == '1' or choice == '2'):
                print("Invalid choice")
                return

            # User wants to add a class
            if choice == '1':
                # Getting information about the class the user wants to add
                className = input("Enter the class name: ")
                while True:
                    classDate = input("Please enter the date that you'd like the class to be on in the format YYYY-MM-DD: ")

                    # Determining if the classDate meets the required format and its a valid classDate
                    if re.match(r'^\d{4}-\d{2}-\d{2}$', classDate):
                        if isValidDate(classDate, 2022):
                            break
                        else:
                            print("You have entered an invalid date. Please enter a valid date after January 1, 2022 (when the gym was opened).")
                    else:
                        print("You have entered an invalid date. Please use the format YYYY-MM-DD (ex. 2023-04-15).")
                
                # Letting the user set the start time for the class
                while True:
                    startTime = input("Please enter the start time of the new class in 24 hr format (HH:MM): ")
                    if re.match(r"^(?:[0-1]?[0-9]|2[0-3]):[0-5][0-9]$", startTime):
                        break
                    else:
                        print("You have entered an invalid start time. Please use the format HH:MM format (ex. 9:30 or 17:30).")

                # Letting the user set the end time for the class
                while True:
                    endTime = input("Please enter the end time of the new class in 24 hr format (HH:MM): ")
                    if re.match(r"^(?:[0-1]?[0-9]|2[0-3]):[0-5][0-9]$", endTime):
                        # Making sure that the endTime is after the startTime before breaking
                        startDateTime = datetime.strptime(startTime, "%H:%M")
                        endDateTime = datetime.strptime(endTime, "%H:%M")
                        
                        if endDateTime > startDateTime:
                            break
                        else:
                            print("You have entered an invalid end time. Please make sure the end time is after start time.")
                    else:
                        print("You have entered an invalid end time. Please use the format HH:MM format (ex. 9:30 or 17:30).")
                
                # Display all the personal trainers's availability
                cursor.execute("SELECT trainerId, availabilityDate, startTime, endTime FROM TrainerAvailability")
                trainerAvailabilities = cursor.fetchall()

                if not(trainerAvailabilities):
                    print("No trainers with availability in the system.")
                    return

                print("Personal Trainer Availabilities:")
                for tAvailability in trainerAvailabilities:
                    print(f"\tTrainer ID: {tAvailability[0]}, Date: {tAvailability[1]}, Time: {tAvailability[2]} to {tAvailability[3]}")

                # Ask for trainer ID
                trainerId = input("Enter the ID of the trainer that will teach this class: ")

                # Check if the trainer is available
                if not checkTrainerAvailability(trainerId, classDate, startTime, endTime):
                    print("Trainer is unavailable to teach this class. Please choose another trainer.")
                    return
                
                # Add class to database with that trainer if this is successful
                cursor.execute("INSERT INTO Class (className, trainerId, classDate, startTime, endTime) VALUES (%s, %s, %s, %s, %s)", (className, trainerId, classDate, startTime, endTime))
                connection.commit()

                print("The class has been added to the database")
                displayAllClasses()

            elif choice == '2':
                displayAllClasses()
                
                # Asking the user for the class ID of the class they want to remove and then removing it if it exists (otherwise displaying a message to the user that it doesn't exist)
                classId = input("Enter the id of the class you'd like to remove: ")
                
                cursor.execute("SELECT * FROM Class WHERE classId = %s", (classId,))
                classInfo = cursor.fetchone()
            
                if not classInfo:
                    print("Invalid class. No class with that class ID in the database.")
                    return

                # Deleting the class from the classes table, and going through MemberTakesClass and delete all entries with a matching classId
                cursor.execute("DELETE FROM MemberTakesClass WHERE classId = %s", (classId,))
                cursor.execute("DELETE FROM Class WHERE classId = %s", (classId,))

                connection.commit()
                print("The class has been removed from the database.")
                displayAllClasses()

        except psycopg2.Error as err:
            print("Error while updating classes:", err)
        finally:
            cursor.close()



    def main():
        while True:
            print("What is your account type? (Select its corresponding number):")
            print("1. Member")
            print("2. Trainer")
            print("3. Administrative Staff")

            try:
                accountType = int(input("Enter your choice (1, 2, or 3): "))
            except ValueError:
                print("Make sure to enter an integer. Please try again.\n")
                continue

            if accountType < 1 or accountType > 3:
                print("You have chosen an invalid number. Please try again.\n")
            else:
                break
        
        if accountType == 1:
            # Let the member decide if they would like to register or log in. 
            choice = input("Enter R to register or L to login? ")

            # If they'd like to register, calling registerUser()
            if choice.upper() == 'R':
                registerUser()
            # otherwise, get email and password and call loginUser(email, pass)
            elif choice.upper() == 'L':
                email = input("Enter your email: ")
                password = input("Enter your password: ")
                member = loginUser(email, password, accountType)
                
                if member:
                    print(f"{member[1]} {member[2]} successfully logged in. Welcome!\n")

                    print("What would you like to do?")
                    print("1. Profile Management")
                    print("2. Dashboard Display")
                    print("3. Schedule Management")
                    
                    while True:
                        try:
                            memberChoice = int(input("Enter your choice (1, 2, or 3): "))
                        except ValueError:
                            print("Make sure to enter an integer. Please try again.\n")
                            continue

                        if memberChoice < 1 or memberChoice > 3:
                            print("You have chosen an invalid number. Please try again.\n")
                        else:
                            break
                    

                    if memberChoice == 1:
                        profileManagement(member[0])
                    elif memberChoice == 2:
                        displayDashboard(member[0])
                    else:
                        userScheduleManagement(member[0])
                
            else:
                print("You have entered \"" + choice + "\". Please enter R or L.")
        
        elif accountType == 2:
            # Let trainer login by getting their email and password, and calling loginTrainer(email, pass)
            email = input("Enter your email: ")
            password = input("Enter your password: ")
            trainer = loginUser(email, password, accountType)

            if trainer:
                print(f"Trainer {trainer[1]} {trainer[2]} successfully logged in. Welcome!\n")

                print("What would you like to do?")
                print("1. Manage Schedule")
                print("2. View Member Profile")

                while True:
                    try:
                        trainerChoice = int(input("Enter your choice (1 or 2): "))
                    except ValueError:
                        print("Make sure to enter an integer. Please try again.\n")
                        continue

                    if trainerChoice < 1 or trainerChoice > 2:
                        print("You have chosen an invalid number. Please try again.\n")
                    else:
                        break
                
                if trainerChoice == 1:
                    print("\nSchedule Management")
                    while True:
                        setAvailability(trainer[0])  # Call the function to set availability
                        continueSettingAvailability = input("Enter Y to set availability for another date or anything else to stop: ")
                        if continueSettingAvailability.upper() != 'Y':
                            break
                elif trainerChoice == 2:
                    firstName = input("What is the member's first name: ")
                    lastName = input("What is the member's last name: ")
                    searchMemberProfile(firstName, lastName)
        
        else:
            # Let staff login by getting their email and password, and calling loginStaff(email, pass)
            email = input("Enter your email: ")
            password = input("Enter your password: ")
            staff = loginUser(email, password, accountType)
            
            if staff:
                print(f"Staff {staff[1]} {staff[2]} successfully logged in. Welcome!\n")

                print("What would you like to do?")
                print("1. Manage Room Bookings")
                print("2. Monitor Equipment Maintenance")
                print("3. Manage Class Scheduling")
                print("4. Bill a user")

                while True:
                    try:
                        staffChoice = int(input("Enter your choice (1, 2, 3, or 4): "))
                    except ValueError:
                        print("Make sure to enter an integer. Please try again.\n")
                        continue

                    if staffChoice < 1 or staffChoice > 4:
                        print("You have chosen an invalid number. Please try again.\n")
                    else:
                        break
                
                if staffChoice == 1:
                    print("\nManage Room Bookings")
                    while True:
                        manageRoomBookings(staff[0])  # Call the function to manage room bookings
                        continueManagingRoomBooking = input("Enter Y to manage another room booking or anything else to stop: ")
                        if continueManagingRoomBooking.upper() != 'Y':
                            break

                elif staffChoice == 2:
                    print("\nEquipment Maintenance")
                    while True:
                        equipmentMaintenanceMonitoring()  # Call the function to manage equipment maintenance
                        continueEquipmentMaintenanceMonitoring = input("Enter Y to manage the maintenance of more equipment or anything else to stop: ")
                        if continueEquipmentMaintenanceMonitoring.upper() != 'Y':
                            break
                
                elif staffChoice == 3:
                    print("\nClass Schedule Update")
                    while True:
                        classScheduleUpdate()
                        continueUpdatingClasses = input("Enter Y to manage more classes or anything else to stop: ")
                        if continueUpdatingClasses.upper() != 'Y':
                            break

                elif staffChoice == 4:
                    print("\nBilling")
                    while True:
                        managePayment()  # Call the function to manage the payment
                        continueBilling = input("Enter Y to manage more payments or anything else to stop: ")
                        if continueBilling.upper() != 'Y':
                            break

    main()

    connection.close()
except (Exception, psycopg2.Error) as err:
    print("Could not connect to the database. Encountered the following error:", err)
    exit()