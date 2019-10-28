import discord
from discord.ext import commands
from dotenv import load_dotenv
from json import load, dump
import os
from random import randint
from rdoclient_py3 import RandomOrgClient, RandomOrgSendTimeoutError, RandomOrgInsufficientRequestsError, RandomOrgInsufficientBitsError

load_dotenv()
# Discourse
with open('data/wiki.json', encoding='utf-8') as json_wiki:
    commands_wiki=load(json_wiki)
with open('data/responses.json', encoding='utf-8') as json_responses:
    responses=load(json_responses)
bot=commands.Bot(command_prefix=os.getenv('DISCORD_COMMAND_PREFIX'))
guild_emoji={}
guild_role_ids={}
guild_role_indexes={}
vowels=['a', 'e', 'i', 'o', 'u']
# Randorg
randorg_client=RandomOrgClient(os.getenv('RANDORG_API_KEY'))

def get_role(guild, name):
    return guild.roles[guild_role_indexes[guild_role_ids[name]]]

def format_emoji(name):
    return '<:{0}:{1}>'.format(name, guild_emoji[name])

@bot.event
async def on_ready():
    guild=bot.get_guild(int(os.getenv('DISCORD_GUILD_ID')))
    # Emoji name to ID
    with open('data/{0}/emoji.json'.format(guild.id), 'w') as json_emoji:
        for emoji in guild.emojis:
            guild_emoji[emoji.name]=emoji.id
        dump(guild_emoji, json_emoji)
    # Role name to ID
    with open('data/{0}/role_ids.json'.format(guild.id), 'w') as json_role_ids:
        for role in guild.roles:
            guild_role_ids[role.name]=role.id
        dump(guild_role_ids, json_role_ids)
    # Role ID to index in guild's role list
    with open('data/{0}/role_indexes.json'.format(guild.id), 'w') as json_role_indexes:
        for i, role in enumerate(guild.roles):
            guild_role_indexes[role.id]=i
        dump(guild_role_indexes, json_role_indexes)

    print(responses['on_ready'].format(guild.me.display_name, bot.user.name, guild.name, guild.id))

@bot.event
async def on_message(message):
    if message.author==bot.user:
        return
    # Commands first for faster query, hopefully.
    await bot.process_commands(message)
    
    message_lowcase=message.content.lower()

    if 'wotcher' in message_lowcase:
        await message.add_reaction(format_emoji('wotcher'))

    if 'rougelike' in message_lowcase:
        await message.channel.send(responses['rougelike'].format(vowels[randint(0, 4)], vowels[randint(0, 4)], vowels[randint(0, 4)]))


@bot.command(description='Search the Library of Maia to learn about various topics.')
async def wiki(context, *entry):
    entry_full=' '.join(entry).lower()

    response='**{0}'.format(entry_full)

    if commands_wiki.get(entry_full):
        # Redirecting entries
        while commands_wiki.get(entry_full)[0]=='>':
            entry_full=commands_wiki.get(entry_full)[1:]
            response+='→{0}'.format(entry_full)

        response+=':** {0}'.format(commands_wiki.get(entry_full))
    else:
        response+=':** {0}'.format(responses['wiki_entry_not_exist'])

    await context.send(response)

@bot.command(description='Bards you and unbards you.')
async def bard(context):
    if get_role(context.guild, 'Bard') in context.author.roles:
        await context.author.remove_roles(get_role(context.guild, 'Bard'), reason=responses['unbard_reason'])
        await context.send(responses['unbard'])
    else:
        await context.author.add_roles(get_role(context.guild, 'Bard'), reason=responses['bard_reason'])
        await context.send(responses['bard'])

@bot.command(description='Powered by Random.org. Rolls dice with the xdy+m format. First word in reason can specify number of repeats.')
async def roll(context, die, *reason):
    nof_repeats=1
    response="{0} `{1}`".format(responses['roll_rolling'], die)
    for i, word in enumerate(reason):
        if not i:
            if word.isdigit():
                nof_repeats=int(word)
                response+=' {0} {1}'.format(word, responses['roll_times'])
                if len(*reason)>1:
                    response+=' {0}'.format(responses['roll_for'])
            else:
                response+=' {0} {1}'.format(responses['roll_once_for'], word)
        else:
            response+=' {0}'.format(word)
    response+=':'
    # Replacing 'd' and '+' with spaces
    die_list=die.translate({100:32, 43:32}).split()
    die_list.append('0')
    dice, sides, mod=int(die_list[0]), int(die_list[1]), int(die_list[2])

    results_dice=[]
    try:
        results_dice.extend(randorg_client.generate_integers(dice*nof_repeats, 1, sides))
    except RandomOrgSendTimeoutError:
        response+='\n{0}'.format(responses['roll_randorg_timeout'])
    except (RandomOrgInsufficientRequestsError, RandomOrgInsufficientBitsError):
        response+='\n{0}'.format(responses['roll_randorg_juice'])
        for _ in range(dice*nof_repeats):
            results_dice.append(randint(1, sides))
    # Actually displaying dice
    for i in range(nof_repeats):
        roll=results_dice[dice*i:dice*(i+1)]
        response+='\n`{0}`→{1}'.format(str(roll), sum(roll)+mod)

    await context.send(response)



bot.run(os.getenv('DISCORD_TOKEN'))

# Todo: !gungeon @mention time_hours reason: Muted!