/** @typedef {{id:number,branch:string,day:string,volume:number,mark:'normal'|'capped'|'unknown',note:string}} DailyVolume */
/** @typedef {{day:string,raw:number,prediction:number,lower:number,upper:number|null,clipped:boolean,basis:string}} FutureDay */
/** @typedef {{id:number,name:string,branch:string,backtest_days:number,alpha:number,beta:number,state:string,result:object,error?:string}} ForecastRun */
/** @typedef {{day:string,lower:number,upper:number|null,lower_staff:number,upper_staff:number|null,staff:number,signable:boolean,signable_reason:string}} ScheduleDay */
/** @typedef {{id:number,run_id:number,capacity:number,model:string,schedule:ScheduleDay[],note:string,status:string}} Staffing */
