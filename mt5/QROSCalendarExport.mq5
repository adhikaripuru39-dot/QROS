#property copyright "QROS"
#property version "1.00"
#property description "Read-only built-in MT5 calendar export. No orders, DLLs or WebRequest."
#property strict

input string OutputFile="QROS\\calendar.json";
input int RefreshSeconds=30;

string Quoted(string value)
{
   StringReplace(value,"\\","\\\\");
   StringReplace(value,"\"","\\\"");
   StringReplace(value,"\r","\\r");
   StringReplace(value,"\n","\\n");
   StringReplace(value,"\t","\\t");
   return "\""+value+"\"";
}

void ExportCalendar()
{
   datetime server_now=TimeTradeServer();
   datetime utc_now=TimeGMT();
   datetime from=server_now-86400;
   datetime until=server_now+7*86400;
   bool complete=(bool)TerminalInfoInteger(TERMINAL_CONNECTED) && server_now>0;
   string currencies[]={"USD","EUR","GBP","JPY","CHF","CAD","AUD"};
   string events=""; int count=0; int errors=0;
   for(int c=0;c<ArraySize(currencies);c++)
   {
      MqlCalendarValue values[];
      ResetLastError();
      int found=CalendarValueHistory(values,from,until,NULL,currencies[c]);
      int error=GetLastError();
      if(found<0 || error!=0 || found>10000)
      {
         complete=false;errors++;continue;
      }
      for(int i=0;i<found;i++)
      {
         MqlCalendarEvent event;
         if(!CalendarEventById(values[i].event_id,event))
         {
            complete=false;errors++;continue;
         }
         if(count>0)events+=",";
         events+="{\"id\":"+Quoted((string)values[i].id)+
            ",\"event_id\":"+Quoted((string)event.id)+
            ",\"name\":"+Quoted(event.name)+
            ",\"currency\":"+Quoted(currencies[c])+
            ",\"importance\":"+(string)(int)event.importance+
            ",\"time_server\":"+(string)(long)values[i].time+
            ",\"exact_time\":"+(event.time_mode==CALENDAR_TIMEMODE_DATETIME?"true":"false")+"}";
         count++;
      }
   }
   // Stamp after the potentially slow query: a long capture must not masquerade
   // as a fresh snapshot. The reader also bounds capture duration.
   datetime finished=TimeGMT();
   string json="{\"schema\":2,\"source\":\"mt5_builtin_calendar\",\"read_only\":true,"+
      "\"generated_utc\":"+(string)(long)utc_now+
      ",\"finished_utc\":"+(string)(long)finished+
      ",\"server_time\":"+(string)(long)server_now+
      ",\"server\":"+Quoted(AccountInfoString(ACCOUNT_SERVER))+
      ",\"query_from_server\":"+(string)(long)from+
      ",\"query_until_server\":"+(string)(long)until+
      ",\"currencies\":[\"USD\",\"EUR\",\"GBP\",\"JPY\",\"CHF\",\"CAD\",\"AUD\"],"+
      "\"complete\":"+(complete?"true":"false")+
      ",\"errors\":"+(string)errors+",\"events\":["+events+"]}";
   FolderCreate("QROS");
   string temporary=OutputFile+".tmp";
   int handle=FileOpen(temporary,FILE_WRITE|FILE_TXT|FILE_ANSI,0,CP_UTF8);
   if(handle==INVALID_HANDLE){Print("QROS calendar file open failed: ",GetLastError());return;}
   uint written=FileWriteString(handle,json);
   FileFlush(handle);FileClose(handle);
   if(written==0 || !FileMove(temporary,0,OutputFile,FILE_REWRITE))
   {Print("QROS calendar publish failed: ",GetLastError());return;}
   Comment("QROS built-in calendar: ",complete?"complete":"FAILED CLOSED",
      "\nEvents: ",count," | Errors: ",errors,"\nRefreshed UTC: ",TimeToString(finished,TIME_DATE|TIME_SECONDS),
      "\nRead-only exporter; no trading functions.");
   Print("QROS calendar exported: complete=",complete," events=",count," errors=",errors);
}

int OnInit()
{
   if(RefreshSeconds<5 || RefreshSeconds>60)return INIT_PARAMETERS_INCORRECT;
   if(!EventSetTimer(RefreshSeconds))return INIT_FAILED;
   ExportCalendar();return INIT_SUCCEEDED;
}
void OnTimer(){ExportCalendar();}
void OnDeinit(const int reason){EventKillTimer();Comment("");}
