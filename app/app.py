import asyncio
import dotenv
import discord
import aiosqlite
import os
import logging
from datetime import datetime
DB_PATH = '/var/data/db.sqlite'

logging.basicConfig(level=logging.INFO)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.members = True
dotenv.load_dotenv()
bot = discord.Bot(intents=intents)
admins = os.getenv("BOT_ADMINS").split(',')
# we need to limit the guilds for testing purposes
# so other users wouldn't see the command that we're testing
ids = os.getenv("GUILD_IDS").split(',')

class user:
    def __init__(self, id, name, credit):
        self.id = id
        self.name = name
        self.credit = credit


async def init():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS user (id INTEGER PRIMARY KEY, username TEXT, credit INTEGER)")
        await db.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, user INTEGER, amount INTEGER, reason TEXT, timestamp TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS rads (id INTEGER PRIMARY KEY, user INTEGER, score INTEGER)")
        await db.commit()


async def insert_credit(id: int, username: str, credit: int, reason: str):
    async with aiosqlite.connect(DB_PATH) as db:
      async with db.execute("SELECT * FROM user where id = ?", (id,)) as cursor:
        row = await cursor.fetchone()
        if row:
          newCredit = row[2] + credit
          await db.execute("UPDATE user SET username = ?, credit = ? WHERE id = ?", (username, newCredit, id))
          await db.commit()
        else:
          await db.execute("INSERT INTO user (id, username, credit) VALUES (?, ?, ?)", (id, username, credit,))
          newCredit = credit
          await db.commit()
        await db.execute("INSERT INTO history (user, amount, reason, timestamp) VALUES (?, ?, ?, ?)", (id, credit, reason, str(datetime.now()),))
        await db.commit()
    return user(id, username, newCredit)


async def check_credit(id: int):
    async with aiosqlite.connect(DB_PATH) as db:
      async with db.execute("SELECT * FROM user where id = ?", (id,)) as cursor:
        row = await cursor.fetchone()
        if row:
            return user(id, row[1], row[2])
        else:
            return None


async def get_credit(id: int):
    async with aiosqlite.connect(DB_PATH) as db:
      async with db.execute("SELECT * FROM user where id = ?", (id,)) as cursor:
        row = await cursor.fetchone()
        if row:
            return row[2]
        else:
            return None



# @bot.slash_command(name="guilds", guild_ids=[763897284730814524])
# # pycord will figure out the types for you
# async def guilds(ctx):
#     await ctx.respond(f"{bot.guilds}")

# , guild_ids=ids
@bot.slash_command(name="credit", description="Give target user social credits")
# pycord will figure out the types for you
async def add_credit(ctx, target: discord.user.User, credit: int, reason: str):
    if str(ctx.user.id) not in admins:
        await ctx.respond("YOU DO NOT HAVE THE RIGHTS TO DO THIS. STRAIGHT TO THE RE-EDUCATION CAMP WITH YOU")
        return

    curUser = await insert_credit(target.id, target.name, credit, reason)

    if credit > 0:
        embed = discord.Embed(
            title="SOCIAL CREDITS",
            description=f"`{curUser.name.upper()}` HAS BEEN AWARDED WITH `{credit}` SOCIAL CREDITS. THEY NOW HAVE `{curUser.credit}` CREDITS. ",
            colour=discord.Colour.green(),
            thumbnail=target.display_avatar.url
        )

    else:
        embed = discord.Embed(
            title="SOCIAL CREDITS",
            description=f"`{curUser.name.upper()}` HAS LOST `{credit}` SOCIAL CREDITS. THEY NOW HAVE `{curUser.credit}` CREDITS.",
            colour=discord.Colour.dark_red(),
            thumbnail=target.display_avatar.url
        )

    embed.add_field(name='Reason', value=reason)
    await ctx.respond(embed=embed)


@bot.slash_command(name="balance", description="Get the balance of the target user")
# pycord will figure out the types for you
async def check_balance(ctx, target: discord.user.User):
    curUser = await check_credit(target.id)
    if curUser and curUser.credit != 0:
        embed = discord.Embed(
            title="SOCIAL CREDITS",
            description = f"`{target.name.upper()}` CURRENTLY HAS `{curUser.credit}` SOCIAL CREDITS",
            color=discord.Colour.blurple(),
            thumbnail=target.display_avatar.url
        )

    else:
        embed = discord.Embed(title='SOCIAL CREDITS',
                              description=f"`{target.name.upper()}` THIS BITCH HAS NO SOCIAL CREDITS. FUCKING LOSER",
                              colour=discord.Colour.brand_red(),
                              thumbnail=target.display_avatar.url
                              )
    await ctx.respond(embed=embed)


@bot.slash_command(name="leaderboard", description="Get a leaderboard of users with the highest social credit")
# pycord will figure out the types for you
async def leaderboard(ctx, order: discord.Option(choices=['high', 'low']) = 'high'):
    num = 1
    members = [member.id for member in ctx.guild.members]
    embed = discord.Embed(
        title="SOCIAL CREDITS LEADERBOARD",
        color=discord.Colour.blurple(),
    )

    if order == 'high':
        order = 'DESC'
    else:
        order = 'ASC'

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(f"SELECT * FROM user ORDER BY credit {order}") as cursor:
            async for row in cursor:
                if row[0] in members:
                    embed.add_field(name=f"{num}. ", value=f"{row[1]} | {row[2]}", inline=False)
                    num += 1

    await ctx.respond(embed=embed)


@bot.slash_command(name="history", description="Get a history of a users social credit")
# pycord will figure out the types for you
async def history(ctx, target: discord.user.User):
    num = 1
    members = [member.id for member in ctx.guild.members]
    embed = discord.Embed(
        title="SOCIAL CREDITS HISTORY",
        color=discord.Colour.blurple(),
        thumbnail=target.display_avatar.url
    )

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(f"SELECT * FROM history WHERE user = ? ORDER BY id DESC", (target.id,)) as cursor:
            async for row in cursor:
                embed.add_field(name=f"{row[4]} ", value=f"{row[2]} | {row[3]}", inline=False)
                num += 1
    await ctx.respond(embed=embed)


@bot.slash_command(name="remove", description="Spend your own credits to remove someone else's credits at a ratio of 2/1")
# pycord will figure out the types for you
async def remove(ctx, target: discord.user.User, amount: int):
    remover = ctx.user.id
    removerCredit = await get_credit(remover)
    if not removerCredit or removerCredit - amount<= 0:
        embed = discord.Embed(
            title="YOU ARE TOO POOR",
            color=discord.Colour.red(),
            thumbnail=ctx.user.display_avatar.url
        )
    else:
        newCredit = int(amount/2)
        await insert_credit(ctx.user.id, ctx.user.name, -amount, f"Spent to remove credits from {target.name}")
        await insert_credit(target.id, target.name, -newCredit, f"Credits removed by {ctx.user.name}")
        embed = discord.Embed(
            title="SOCIAL CREDITS REMOVED",
            description=f"{ctx.user.name} spent {amount} to have {newCredit} credits removed from {target.name}",
            color=discord.Colour.red(),
            thumbnail=target.display_avatar.url
        )
    await ctx.respond(embed=embed)


@bot.slash_command(name="give", description="Transfer an amount of credits to another user")
# pycord will figure out the types for you
async def give(ctx, target: discord.user.User, amount: int):
    giver = ctx.user.id
    giverCredit = await get_credit(giver)
    if not giverCredit or giverCredit - amount <= 0:
        embed = discord.Embed(
            title="YOU ARE TOO POOR",
            color=discord.Colour.red(),
            thumbnail=ctx.user.display_avatar.url
        )
    else:
        if amount < 0:
            embed = discord.Embed(
            title="You cannot give negative credits",
            color=discord.Colour.red(),
            thumbnail=ctx.user.display_avatar.url
        )
        else:
            await insert_credit(ctx.user.id, ctx.user.name, -amount, f"Transfered credits to {target.name}")
            await insert_credit(target.id, target.name, amount, f"Received a transfer from {ctx.user.name}")
            embed = discord.Embed(
                title="SOCIAL CREDITS TRANSFERED",
                description=f"{ctx.user.name} has sent {amount} credits to {target.name}",
                color=discord.Colour.blurple(),
                thumbnail=target.display_avatar.url
            )
    await ctx.respond(embed=embed)


@bot.slash_command(name="setrads", description="Set the rads test score of target user")
# pycord will figure out the types for you
async def set_rads(ctx, target: discord.user.User, score: int):
    if str(ctx.user.id) not in admins and ctx.user.id != target.id:
        embed = embed = discord.Embed(
            title="YOU ARE NOT ALLOWED TO ASSIGN THIS AUTISM SCORE",
            color=discord.Colour.red(),
            thumbnail=ctx.user.display_avatar.url,
        )
        await ctx.respond(embed=embed)
        return 
    
    embed = discord.Embed(
        title="RADS SCORE SET",
        color=discord.Colour.blurple(),
        thumbnail=target.display_avatar.url,
        description=f"{target.name} was assigned a RADS score of {score}"
    )

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(f"SELECT * FROM rads WHERE user = ?", (target.id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                await db.execute("UPDATE rads SET score = ? where user = ?", (score, target.id,))
                await db.commit()
            else:
                await db.execute("INSERT INTO rads (user, score) VALUES (?, ?) ", (target.id, score))
                await db.commit()

    await ctx.respond(embed=embed)


@bot.slash_command(name="getrads", description="Get the rads test score of target user")
# pycord will figure out the types for you
async def get_rads(ctx, target: discord.user.User):
    

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(f"SELECT * FROM rads WHERE user = ?", (target.id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                score = row[2]
            else:
                score = 'UNSET'

    embed = discord.Embed(
        title="RADS SCORE",
        color=discord.Colour.blurple(),
        thumbnail=target.display_avatar.url,
        description=f"{target.name} has a RADS score of {score}"
    )
    await ctx.respond(embed=embed)



@bot.slash_command(name="radsboard", description="Get a leaderboard of users with the highest RADS score")
# pycord will figure out the types for you
async def rads_board(ctx, order: discord.Option(choices=['high', 'low']) = 'high'):
    num = 1
    members = [member.id for member in ctx.guild.members]
    embed = discord.Embed(
        title="RADS-R LEADERBOARD",
        color=discord.Colour.blurple(),
    )

    if order == 'high':
        order = 'DESC'
    else:
        order = 'ASC'

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(f"SELECT * FROM rads ORDER BY score {order}") as cursor:
            async for row in cursor:
                if row[1] in members:
                    user = await bot.fetch_user(row[1])
                    embed.add_field(name=f"{num}. ", value=f"{user.name} | {row[2]}", inline=False)
                    num += 1

    await ctx.respond(embed=embed)


asyncio.run(init())
token = str(os.getenv("TOKEN"))
bot.run(token)

