#include <Wire.h>
#include <INA3221.h>


INA3221 ina_1(INA3221_ADDR40_GND);
unsigned long lastHb;
int ma_duty, mb_duty;

const int ma_dir = 26;
const int mb_dir = 32;
const int ma_pwm = 25;
const int mb_pwm = 33;


void initIna(){
  ina_1.begin(&Wire);
  ina_1.reset();
  ina_1.setShuntRes(100, 100, 100);
}

void expiredAllStop(){
  ledcWriteChannel(0, 0);
  ledcWriteChannel(1, 0);
}

void commsLog(){
  lastHb = millis();
}

void handleHeartBeat(){
  Serial.println("heartbeat");
  commsLog();
}

bool isHbExpired(){
  if((millis() - lastHb) > 1000){
    expiredAllStop();
    return true;
  } else {
    return false;
  }
}

void handlePowerRequest(){
  
  String ch1_ma = String(ina_1.getCurrent(INA3221_CH1) * 1000);
  String ch2_ma = String(ina_1.getCurrent(INA3221_CH2) * 1000);
  String ch3_ma = String(ina_1.getCurrent(INA3221_CH3) * 1000);

  String ch1_v = String(ina_1.getVoltage(INA3221_CH1));
  String ch2_v = String(ina_1.getVoltage(INA3221_CH2));
  String ch3_v = String(ina_1.getVoltage(INA3221_CH3));

  Serial.println(ch1_v + " " + ch1_ma + " " + ch2_v + " " + ch2_ma + " " + ch3_v + " " + ch3_ma);
  commsLog();
}

void handleMotorRequest(String command){
  int duty = 0;
  if(command.startsWith("ma")){
    duty = command.substring(command.indexOf(" "), command.length()).toInt();
    if(duty < 0){
      digitalWrite(ma_dir, LOW);
    } else {
      digitalWrite(ma_dir, HIGH);
    }
    ledcWriteChannel(0, abs(duty));
  }
  if(command.startsWith("mb")){
    duty = command.substring(command.indexOf(" "), command.length()).toInt();
    if(duty < 0){
      digitalWrite(mb_dir, LOW);
    } else {
      digitalWrite(mb_dir, HIGH);
    }
    ledcWriteChannel(1, abs(duty));
  }
  commsLog();
}

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(5000);
  initIna();
  pinMode(ma_dir, OUTPUT);
  pinMode(mb_dir, OUTPUT);
  ledcAttachChannel(ma_pwm, 500, 8, 0);
  ledcAttachChannel(mb_pwm, 500, 8, 1);
}

void loop() {
  // put your main code here, to run repeatedly:
  if(Serial.available() == 0){
    isHbExpired();
    delay(1);
  } else {
    String eval = Serial.readStringUntil('\n');

    if(eval.startsWith("heartbeat")){
      handleHeartBeat();
    }

    if(eval.startsWith("pwr")){
      handlePowerRequest();
    }

    if(eval.startsWith("ma")){
      handleMotorRequest(eval);
    }

    if(eval.startsWith("mb")){
      handleMotorRequest(eval);
    }
  }

  
  
}
