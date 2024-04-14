-- Each member will have a userId and will enter their first name, last name, email, password, birth date, phone number, and can optionally enter their weight and body fat percentage
CREATE TABLE Member (
    userId SERIAL PRIMARY KEY,
    fName VARCHAR(20) NOT NULL,
    lName VARCHAR(20) NOT NULL,
    email VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL,
    dateOfBirth DATE CHECK(dateOfBirth>='1901-1-1') NOT NULL, 
    phoneNumber CHAR(14) NOT NULL,
    weightLbs NUMERIC(5, 2),
    bodyFatPercentage NUMERIC (3, 1)
);

-- Members can create their own achievements/goals that they'd like to accomplish. We track if the achievement is achieved (if the date is null or not) and the date that it is achieved and modify the date achieved accordingly.
CREATE TABLE Achievement (
    achievementId SERIAL PRIMARY KEY,
    userId INT NOT NULL,
    achievementName VARCHAR(50) NOT NULL,
    achievementDescription TEXT,
    dateAchieved DATE DEFAULT NULL,
    FOREIGN KEY (userId) REFERENCES Member(userId)
);

CREATE TABLE PersonalTrainer (
    trainerId SERIAL PRIMARY KEY,
    fName VARCHAR(20) NOT NULL,
    lName VARCHAR(20) NOT NULL,
    email VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL,
    phoneNumber CHAR(14) NOT NULL
);

CREATE TABLE TrainerAvailability (
    availibilityId SERIAL PRIMARY KEY,
    trainerId INT NOT NULL,
    availabilityDate DATE NOT NULL,
    startTime TIME NOT NULL,
    endTime TIME NOT NULL,
    FOREIGN KEY (trainerId) REFERENCES PersonalTrainer(trainerId)
);

CREATE TABLE AdministrativeStaff (
    staffId SERIAL PRIMARY KEY,
    fName VARCHAR(20) NOT NULL,
    lName VARCHAR(20) NOT NULL,
    email VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL,
    phoneNumber CHAR(14) NOT NULL
);

CREATE TABLE Equipment (
    equipmentId SERIAL PRIMARY KEY,
    equipmentName VARCHAR(100),
    underMaintenance BOOLEAN DEFAULT FALSE
);

CREATE TABLE EquipmentMaintenance (
    maintenanceId SERIAL PRIMARY KEY,
    equipmentId INT NOT NULL,
    maintenanceCompletionDate TIMESTAMP DEFAULT NULL,
    FOREIGN KEY (equipmentId) REFERENCES Equipment(equipmentId)
);

CREATE TABLE Room (
    roomNumber INT PRIMARY KEY,
    roomName VARCHAR(20) UNIQUE
);

-- Rooms can be booked by trainers.
CREATE TABLE RoomBookings(
    roomBookingId SERIAL PRIMARY KEY,
    roomNumber INT NOT NULL,
    bookingDate DATE NOT NULL,
    startTime TIME NOT NULL,
    endTime TIME NOT NULL,
    bookingStaffId INT NOT NULL,
    FOREIGN KEY (roomNumber) REFERENCES Room(roomNumber),
    FOREIGN KEY (bookingStaffId) REFERENCES AdministrativeStaff(staffId)
);

CREATE TABLE Class (
    classId SERIAL PRIMARY KEY,
    className VARCHAR(50) NOT NULL,
    trainerId INT NOT NULL,
    classDate DATE NOT NULL,
    startTime TIME NOT NULL,
    endTime TIME NOT NULL,
    FOREIGN KEY(trainerId) REFERENCES PersonalTrainer(trainerId)
);

CREATE TABLE MemberTakesClass (
    userId INT NOT NULL,
    classId INT NOT NULL,
    PRIMARY KEY (userId, classId),
    FOREIGN KEY (userId) REFERENCES Member(userId),
    FOREIGN KEY (classId) REFERENCES Class(classId)
);

CREATE TABLE PersonalTrainingSession (
    sessionId SERIAL PRIMARY KEY,
    userId INT NOT NULL,
    trainerId INT NOT NULL,
    sessionDate DATE NOT NULL,
    startTime TIME NOT NULL,
    endTime TIME NOT NULL,
    FOREIGN KEY (trainerId) REFERENCES PersonalTrainer(trainerId),
    FOREIGN KEY (userId) REFERENCES Member(userId) 
);

-- Exercises will be populated by my DML and the user will able to choose from exercises. They will also optionally have some sort of description
CREATE TABLE Exercise (
    exerciseId SERIAL PRIMARY KEY,
    exerciseName VARCHAR(50) UNIQUE NOT NULL,
    exerciseDescription TEXT
);

-- Users will have one to many routines associated with them (that they create for themselves)
CREATE TABLE Routine (
    routineId SERIAL PRIMARY KEY,
    routineName VARCHAR(50) NOT NULL,
    userId INT NOT NULL,
    routineDescription TEXT,
    FOREIGN KEY (userId) REFERENCES Member(userId)
);

-- Routines will consist of many exercises and a specific number of sets for each exercise. One routine can have many exercises, and an exercise can be in multiple routines.
CREATE TABLE RoutineExerciseAssignment (
    routineExerciseId SERIAL PRIMARY KEY,
    routineId INT NOT NULL,
    exerciseId INT NOT NULL,
    numSets SMALLINT NOT NULL,
    FOREIGN KEY (routineId) REFERENCES Routine(routineId),
    FOREIGN KEY (exerciseId) REFERENCES Exercise(exerciseId)
);

CREATE TABLE Payment (
    billNumber SERIAL PRIMARY KEY,
    memberId INT NOT NULL,
    paymentAmount NUMERIC(7, 2) NOT NULL,
    paymentStatus VARCHAR(16),
    statusUpdateDate TIMESTAMP DEFAULT NULL,
    FOREIGN KEY (memberId) REFERENCES Member(userId),
    CONSTRAINT validStatus CHECK (paymentStatus IN ('Awaiting Payment', 'Paid', 'Returned', 'Cancelled'))
);