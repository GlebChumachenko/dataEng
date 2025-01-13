from decouple import config as myconfig
import psycopg2
import pandas as pd
class DBConnect:
    #Подключение к БД
    def __init__(self, user=myconfig('PG_USER'),
                 password=myconfig('PG_PASSWORD'),
                 host=myconfig('PG_HOST'),
                 port=myconfig('PG_PORT'),
                 database=myconfig('PG_DATABASE')):
        self.connection = psycopg2.connect(host=host,
                                           port=port,
                                           database=database,
                                           user=user,
                                           password=password, )

        self.connection.autocommit = True

    #Функция выполняющая запрос и выводит результат в виде таблицы
    def selectUser (self):
        with self.connection.cursor() as cursor:
            cursor.execute("""with filtered_messages as (
    select 
        message_id,
        entity_id,
        type,
        created_by,
        to_timestamp(created_at) at time zone 'UTC' as created_at_ts,
        lag(to_timestamp(created_at) at time zone 'UTC') 
            over (partition by entity_id order by created_at) as client_created_at_ts,
            row_number() over (partition by entity_id, type order by created_at) as rn
    from test.chat_messages
    --WHERE type IN ('incoming_chat_message', 'outgoing_chat_message')
),
avgtime_count as (
	select entity_id, created_by, created_at_ts, client_created_at_ts, 
	(case
		when created_at_ts::time >= '09:30:00'::time and client_created_at_ts::time >= '09:30:00'::time
		then EXTRACT(EPOCH FROM (created_at_ts - client_created_at_ts)) / 60
		when created_at_ts::time >= '09:30:00'::time and client_created_at_ts::time < '09:30:00'::time
		then EXTRACT(EPOCH FROM (created_at_ts::time - '09:30:00'::time)) / 60
		when created_at_ts::time < '09:30:00'::time and client_created_at_ts::time < '09:30:00'::time
		then 0
		when created_at_ts::date = client_created_at_ts::date + interval '1 day'
		 and created_at_ts::time >= '09:30:00'::time and client_created_at_ts::time >= '09:30:00'::time
		then EXTRACT(EPOCH FROM ((('24:00:00'::time-client_created_at_ts::time) +'09:30:00'::time)-created_at_ts::time)) / 60
		when created_at_ts::date = client_created_at_ts::date + interval '1 day'
		 and created_at_ts::time < '09:30:00'::time and client_created_at_ts::time >= '09:30:00'::time 
		then EXTRACT(EPOCH FROM ('24:00:00'::time-client_created_at_ts::time)) / 60 
		else null
		end
	)avrg
	from filtered_messages
	where type = 'outgoing_chat_message'
    and rn = 1
    and client_created_at_ts is not null
)
select r.rop_name, m.name_mop, ROUND(AVG(ac.avrg), 2) as average_time
from avgtime_count ac
inner join test.managers m on m.mop_id =ac.created_by
inner join test.rops r on m.rop_id = cast(r.rop_id as varchar)
where ac.avrg is not null
group by  m.name_mop, r.rop_name


""")
            result = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(result, columns=columns)
            return df

#Вызов функции
if __name__ == "__main__":
    db=DBConnect().selectUser()
    print(db)
