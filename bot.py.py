import discord
from discord.ext import commands
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 1. حط أيدي الروم المخصص هنا
TARGET_CHANNEL_ID = 1536233483121201253  

# 2. حط أيدي رتبة الإدارة أو المشرفين هنا (اللي مسموح لهم يزيدون، ينقصون، ويشوفون ساعات غيرهم)
ADMIN_ROLE_ID = 1527141057442091149  

active_sessions = {}
user_hours = {}

@bot.event
async def on_ready():
    print(f"البوت اشتغل بنجاح باسم: {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()
    parts = content.split()
    cmd = parts[0] if parts else ""

    # دالة بسيطة للتحقق إذا الشخص إداري (عنده رتبة الإدارة أو صلاحية Administrator)
    is_admin = message.author.guild_permissions.administrator or any(role.id == ADMIN_ROLE_ID for role in message.author.roles)

    # --- 1. الأوامر في الروم المخصص (د، خ) ---
    if message.channel.id == TARGET_CHANNEL_ID:
        
        # تسجيل الدخول (د)
        if content == "د":
            user_id = message.author.id
            if user_id in active_sessions:
                await message.channel.send("أنت مسجل دخول بالفعل.")
                return
            
            in_voice = message.author.voice is not None
            active_sessions[user_id] = {'time': datetime.now(), 'voice': in_voice, 'warned': False}
            
            embed = discord.Embed(title="طلب تسجيل دخول", color=0x2ecc71)
            embed.add_field(name="الشخص", value=message.author.mention, inline=False)
            embed.add_field(name="الرومات الصوتية", value="✅" if in_voice else "❌", inline=True)
            embed.add_field(name="داخل السيرفر", value="✅", inline=True)
            embed.add_field(name="حالة الطلب", value="مقبول", inline=False)
            embed.add_field(name="الوقت والتاريخ:", value=datetime.now().strftime("%H:%M %Y/%m/%d"), inline=False)
            
            await message.channel.send(embed=embed)
            return

        # تسجيل الخروج (خ)
        elif content == "خ":
            user_id = message.author.id
            if user_id in active_sessions:
                start_time = active_sessions[user_id]['time']
                duration = datetime.now() - start_time
                hours = int(duration.total_seconds() // 3600)
                minutes = int((duration.total_seconds() % 3600) // 60)
                
                total_mins = int(duration.total_seconds() // 60)
                user_hours[user_id] = user_hours.get(user_id, 0) + total_mins
                
                del active_sessions[user_id]
                
                embed = discord.Embed(title="طلب تسجيل خروج", color=0xe74c3c)
                embed.add_field(name="الشخص", value=message.author.mention, inline=False)
                embed.add_field(name="المدة المحسوبة", value=f"{hours} ساعة و {minutes} دقيقة", inline=False)
                
                await message.channel.send(embed=embed)
            else:
                await message.channel.send(f"{message.author.mention}، أنت لم تقم بتسجيل الدخول بـ 'د' مسبقاً!")
            return

    # --- 2. أمر عرض الساعات (س) ---
    if cmd == "س":
        # لو منشن شخص، يتاكد أولاً هل هو إداري؟
        if message.mentions:
            if not is_admin:
                await message.channel.send("عذراً، هذا الأمر مخصص للإدارة فقط.")
                return
            target_user = message.mentions[0]
        else:
            target_user = message.author  # لو كتب س لوحده تطلع ساعات نفسه

        total_mins = user_hours.get(target_user.id, 0)
        hours = total_mins // 60
        mins = total_mins % 60
        
        embed = discord.Embed(title="ساعات العمل", description=f"مجموع ساعات {target_user.mention} هي: **{hours} ساعة و {mins} دقيقة**.", color=0x3498db)
        await message.channel.send(embed=embed)
        return

    # --- 3. أوامر الإدارة (زيادة، نقص، الغاء دخول) ---
    if is_admin and message.mentions:
        target_user = message.mentions[0]
        
        # زيادة الساعات
        if cmd == "زياده" and len(parts) >= 2:
            try:
                val = float(parts[1])
                added_mins = int(val * 60)
                user_hours[target_user.id] = user_hours.get(target_user.id, 0) + added_mins
                await message.channel.send(f"تم زيادة {parts[1]} ساعة لـ {target_user.mention} بنجاح.")
            except ValueError:
                await message.channel.send("الرجاء كتابة الرقم بشكل صحيح (مثال: زياده 2.00 @شخص)")
            return

        # نقص الساعات
        elif cmd == "نقص" and len(parts) >= 2:
            try:
                val = float(parts[1])
                sub_mins = int(val * 60)
                current = user_hours.get(target_user.id, 0)
                user_hours[target_user.id] = max(0, current - sub_mins)
                await message.channel.send(f"تم نقص {parts[1]} ساعة من {target_user.mention} بنجاح.")
            except ValueError:
                await message.channel.send("الرجاء كتابة الرقم بشكل صحيح (مثال: نقص 2.00 @شخص)")
            return

        # إلغاء الدخول
        elif "الغاء" in content and "دخول" in content:
            if target_user.id in active_sessions:
                del active_sessions[target_user.id]
                await message.channel.send(f"تم إلغاء تسجيل دخول {target_user.mention} ولم يُحتسب له أي وقت.")
            else:
                await message.channel.send(f"العضو {target_user.mention} ليس مسجل دخول أصلاً.")
            return

    await bot.process_commands(message)

# --- 4. مراقبة الرومات الصوتية ---
@bot.event
async def on_voice_state_update(member, before, after):
    if member.id in active_sessions:
        if before.channel is not None and after.channel is None:
            active_sessions[member.id]['warned'] = True
            try:
                embed = discord.Embed(
                    title="تنبيه تسجيل الدخول",
                    description="🕹️ تم رصُد خروجك من الرومات الصوتية. لديك 10 دقائق للعودة قبل إلغاء تسجيل الدخول.",
                    color=0xf1c40f
                )
                embed.add_field(name="الشرط المفقود", value="الرومات الصوتية", inline=False)
                embed.add_field(name="المهلة", value="10 دقائق", inline=False)
                embed.set_footer(text=f"الوقت والتاريخ: {datetime.now().strftime('%H:%M %Y/%m/%d')}")
                await member.send(embed=embed)
            except Exception:
                pass

        elif before.channel is None and after.channel is not None:
            if active_sessions[member.id].get('warned', False):
                active_sessions[member.id]['warned'] = False
                try:
                    embed = discord.Embed(
                        title="تم رصد عودتك",
                        description="✅ تم رصد عودتك الى الرومات الصوتية والسيرفر. تم إلغاء تنبيه فقدان الشرط.",
                        color=0x2ecc71
                    )
                    embed.add_field(name="الشرط المستعاد", value="الرومات الصوتية والسيرفر", inline=False)
                    embed.set_footer(text=f"الوقت والتاريخ: {datetime.now().strftime('%H:%M %Y/%m/%d')}")
                    await member.send(embed=embed)
                except Exception:
                    pass
import os
bot.run(os.getenv('DISCORD_TOKEN'))
