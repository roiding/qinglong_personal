'''
name: glados签到
cron: 30 8 * * *
'''
import os
import requests
glados_token=os.environ.get("glados_token","9037725680843507643281407025606-900-1440")
glados_cookies=os.environ.get("glados_cookies","koa:sess=eyJjb2RlIjoiSjlDMTktTVE0WVctUEUwRzktNjJGUDMiLCJ1c2VySWQiOjY1MDY1NiwiX2V4cGlyZSI6MTc4Njk2MTI4NTE3NiwiX21heEFnZSI6MjU5MjAwMDAwMDB9; koa:sess.sig=AEgLaqvobB8afqPPgCNhqfkeRs4")
response=requests.post("https://glados.space/api/user/checkin",json={"token":"glados.one"},headers={
    "Authorization" : glados_token,
    "Cookie" : glados_cookies,
    "User-Agent" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
}).json()