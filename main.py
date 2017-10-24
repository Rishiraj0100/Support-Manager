import discord
import sqlib
import re
import time
import json
import urllib.request

client = discord.Client()

bot_admins = ['269959141508775937']

helpmsg = {}

helpmsg['ticket'] = "Syntax:\n" \
                    "`{prefix}ticket add [info about the problem]` or\n" \
                    "`{prefix}ticket show [ticket number]`\n" \
                    "`{prefix}ticket close [ticket number]; [reason]`\n" \
                    "The info can't be longer than 100 characters.\n" \
                    "A ticket can only be closed by the author or an admin."

helpmsg['tickets'] = "It's to see all tickets of . . .\n" \
                     ". . . every server:\n" \
                     "  `{prefix}tickets all`\n" \
                     ". . . this server:\n" \
                     "  `{prefix}tickets here`\n" \
                     ". . . a specific user:\n" \
                     "  `{prefix}tickets @[user]`"

helpmsg['addinfo'] = "This is to add information to an existing ticket.\n" \
                     "It can only be used by the ticket author.\n" \
                     "Syntax: `{prefix}addinfo [ticket number] [info]`"

helpmsg['channel'] = "This is to set the 'support-channel', where the bot informs the supporters about:\n" \
                     " - new tickets\n" \
                     " - edited tickets\n" \
                     " - closed tickets\n" \
                     "Syntax: `{prefix}channel #[channel name]`\n" \
                     "This command is only usable for admins."

helpmsg['supprole'] = "Admins should set a support-role like this:\n" \
                      "`{prefix}supprole @[support-role]`\n" \
                      "This role will be mentioned on ticket events."

helpmsg['prefix'] = "This is to change the command prefix of the bot.\n" \
                    "The default prefix is `/` and the current is `{prefix}`.\n" \
                    "If the current prefix is in complication with the prefixes of other bots on this server, " \
                    "an **admin** can change it like this:\n" \
                    "`{prefix}prefix [new prefix]`"

helpmsg['help'] = "`{prefix}help` shows this help message.\n" \
                  "Type `help` after any command to see the command-specific help-page!\n" \
                  "For example: `{prefix}ticket help`"

helpmsg['invite'] = "I'll send you an link to invite me to your server.\n" \
                    "Just type `{prefix}invite`!"


def close_invalids():
    for ticket in sqlib.tickets.get_all():
        ticket_nr = ticket[0]
        
        if ticket[5] == 1:
            continue

        server = client.get_server(ticket[2])
        
        if server is None:
            sqlib.tickets.update(ticket_nr, {'closed': 1})
        
    return sqlib.tickets.get_all()


def post_to_dbotsorg():
    count_json = json.dumps({
        "server_count": len(client.servers)
    })

    # Resolve HTTP redirects
    dbotsorg_redirect_url = urllib.request.urlopen(
        "https://discordbots.org/api/bots/{0}/stats".format(client.user.id)
    ).geturl()

    # Construct request and post server count
    dbotsorg_req = urllib.request.Request(dbotsorg_redirect_url)

    dbotsorg_req.add_header(
        "Content-Type",
        "application/json"
    )

    dbotsorg_req.add_header(
        "Authorization",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjM2MDgwMTg1OTQ2MTQ0NzcwMCIsImJvdCI6"  # API token
        "dHJ1ZSwiaWF0IjoxNTA4NzY0NDk1fQ.EvZ5kvTUP7r1OguZC_3gTiXxrqQitoAgQ2KLKM-4JZ0"
    )

    urllib.request.urlopen(dbotsorg_req, count_json.encode("ascii"))


@client.event
async def on_ready():
    print(client.user.name)
    print("--------------")

    for server in client.servers:
        if sqlib.servers.get(server.id) is None:
            sqlib.servers.add_element(server.id, {'prefix': '/'})

    # print(list(map(lambda s: s.name, client.servers)))
    post_to_dbotsorg()


@client.event
async def on_message(message):
    if message.channel.is_private:
        if message.author != client.user:
            await client.send_message(message.channel, "Sorry, I can't help you in a private chat.")
        return 0

    client_member = message.server.get_member(client.user.id)
    if not client_member.permissions_in(message.channel).send_messages:
        return 0

    prefix = sqlib.servers.get(message.server.id, 'prefix')[0]

    commands = ['tickets', 'ticket', 'addinfo', 'channel', 'supprole', 'help', 'prefix', 'invite']

    if message.content.lower().startswith(tuple(map(lambda com: prefix + com, commands))):
        await client.send_typing(message.channel)
    else:
        if client.user in message.mentions:
            await client.send_message(message.channel, "Type `{0}help` to see available commands.".format(prefix))
        return 0  # Attention to this when adding new commands.

    if message.content.lower().startswith(prefix + 'tickets'):
        content = message.content[9:]

        if content == 'help':
            help_embed = discord.Embed(
                title='Tickets',
                description=helpmsg['tickets'].format(prefix=prefix),
                color=0x37ceb2
            )
            await client.send_message(message.channel, embed=help_embed)
            return 0

        tickets = close_invalids()

        if content.lower().startswith('all'):
            tickets_embed = discord.Embed(
                title="All active tickets.",
                description="Every ticket of every server.",
                color=0x37ceb2
            )

            for ticket in tickets:
                ticket_nr = ticket[0]

                if ticket[5] == 1:
                    continue

                author = await client.get_user_info(ticket[1])

                server = client.get_server(ticket[2])

                tickets_embed.add_field(
                    name="#" + ticket_nr,
                    value="**Author:** {0}\n"
                          "**Info:** {1}\n"
                          "**Server:** *{2}*".format(author.mention, ticket[3], server.name),
                    inline=False
                )

        elif content.lower().startswith('here'):
            tickets_embed = discord.Embed(
                title="Active tickets.",
                description="Every ticket of this server.",
                color=0x37ceb2
            )

            for ticket in tickets:
                ticket_nr = ticket[0]

                if ticket[5] == 1 or ticket[2] != message.server.id:
                    continue

                author = await client.get_user_info(ticket[1])

                tickets_embed.add_field(
                    name="#" + ticket_nr,
                    value="**Author:** {0}\n"
                          "**Info:** {1}".format(author.mention, ticket[3]),
                    inline=False
                )

        elif len(content) == 0:
            await client.send_message(message.channel, "Which tickets?\n"
                                                       "Type `{0}tickets help` to see how it works.".format(prefix))
            return 0

        else:
            member = message.mentions[0]

            tickets_embed = discord.Embed(
                title="User tickets.",
                description="Every active ticket of {0}.".format(member.mention),
                color=0x37ceb2
            )

            for ticket in tickets:
                ticket_nr = ticket[0]

                if ticket[5] == 1 or ticket[1] != member.id:
                    continue

                server = client.get_server(ticket[2])

                tickets_embed.add_field(
                    name="#" + ticket_nr,
                    value="**Info:** {0}\n"
                          "**Server:** *{1}*".format(ticket[3], server.name),
                    inline=False
                )

        if len(tickets_embed.fields) == 0:
            await client.send_message(message.channel, "There are no active tickets.")
            return 0

        tickets_embed.set_footer(
            text="To see also the added info of an ticket use the 'ticket show' command."
        )

        await client.send_message(message.channel, embed=tickets_embed)

    elif message.content.lower().startswith(prefix + "ticket"):
        content = message.content[8:]

        if content == 'help':
            help_embed = discord.Embed(
                title='Ticket',
                description=helpmsg['ticket'].format(prefix=prefix),
                color=0x37ceb2
            )
            await client.send_message(message.channel, embed=help_embed)
            return 0

        channel_id = str(sqlib.servers.get(message.server.id, 'channel')[0])
        channel = client.get_channel(channel_id)
        if channel_id == '0':
            await client.send_message(
                message.channel,
                "It seems there is no support channel configured. :confused:\n"
                "Ask an admin to set one up!"
            )
            return 0

        if channel is None:
            await client.send_message(message.channel, "The configured support channel doesn't exist anymore.\n"
                                                       "Ask an admin to set up a new one.")
            return 0

        if content.lower().startswith("add"):
            content = content[4:].replace('\n', ' ')

            if len(content) > 100:
                await client.send_message(message.channel, "Too many characters, no ticket has been created.\n"
                                                           "Please don't make the info-text longer than 100 chars!")
                return 0

            elif len(content) == 0:
                await client.send_message(message.channel, "Whats your problem? "
                                                           "If you don't tell it, nobody can help you.")
                return 0

            ticket_nr = str(len(sqlib.tickets.get_all())+1)
            sqlib.tickets.add_element(ticket_nr, {'author': message.author.id,
                                                  'server': message.server.id,
                                                  'info': content,
                                                  'added': "{}",
                                                  'closed': 0})

            ticket_embed = discord.Embed(
                title="New ticket",
                color=0x37ceb2
            )
            ticket_embed.add_field(
                name="Ticket number:",
                value=str(ticket_nr),
            )
            ticket_embed.add_field(
                name="Author:",
                value=message.author.mention
            )
            ticket_embed.add_field(
                name="Info:",
                value=content
            )

            supprole_id = sqlib.servers.get(message.server.id, 'role')[0]
            if supprole_id != '0':
                print(supprole_id)
                supprole = discord.utils.find(lambda r: r.id == supprole_id, message.server.roles)

                if supprole is None:
                    await client.send_message(message.channel, "It seems like the support-role doesn't exist anymore. "
                                                               ":confused:")
                    return 0
                await client.send_message(channel, supprole.mention, embed=ticket_embed)

            else:
                await client.send_message(channel, embed=ticket_embed)
            await client.send_message(message.channel, "Ticket created :white_check_mark: \n"
                                                       "Your ticket has the number {0}.".format(ticket_nr))

        if content.lower().startswith("show"):
            content = content[5:]
            close_invalids()

            ticket = sqlib.tickets.get(content)

            if ticket is None:
                await client.send_message(message.channel, "Given ticket can't be found.")
                return 0
            else:
                ticket = list(ticket)  # change tuple to list, to change the values

            if ticket[5] == 1:
                await client.send_message(message.channel, "This ticket is closed.")
                return 0

            ticket_embed = discord.Embed(
                title="Support ticket #{0}".format(content),
                color=0x37ceb2
            )

            author = await client.get_user_info(ticket[1])
            ticket[1] = author.mention

            server = client.get_server(ticket[2])
            ticket[2] = server.name

            added_dict = json.loads(ticket[4].replace("'", '"'))
            ticket[4] = ""
            for date in added_dict:
                ticket[4] += "**{date}:** {info}\n".format(date=date, info=added_dict[date])

            if len(ticket[4]) == 0:
                ticket[4] = "*Nothing added.*"

            column_names = ['Ticket number', 'Author', 'Server', 'Info', 'Added', 'closed']

            counter = 0
            for info in ticket:
                if counter == 5:
                    continue

                ticket_embed.add_field(
                    name=column_names[counter],
                    value=info
                )
                counter += 1

            await client.send_message(message.channel, embed=ticket_embed)

        if content.lower().startswith("close"):
            content = content[6:]
            splited = content.split(';')
            if len(splited) > 1:
                closemsg = splited[1]
                content = splited[0]
            else:
                closemsg = ""

            ticket = sqlib.tickets.get(content)

            if ticket is None:
                await client.send_message(message.channel, "Given ticket can't be found.")
                return 0

            if ticket[5] == 1:
                await client.send_message(message.channel, "Ticket is already closed.")
                return 0

            if ticket[1] != message.author.id:
                if (not message.author.server_permissions.administrator) and (message.author.id not in bot_admins):

                    is_supporter = False
                    for role in message.author.roles:
                        if role.id == sqlib.servers.get(message.server.id, 'role')[0]:
                            is_supporter = True
                            break

                    if not is_supporter:
                        await client.send_message(message.channel, "You have to be admin, supporter or "
                                                                   "ticket author for that.")
                        return 0

                elif ticket[2] != message.server.id and message.author.id not in bot_admins:
                    await client.send_message(message.channel, "This ticket is from an other server.")
                    return 0

                msg_to_user = "**Hey, {0} just closed your ticket #{1}:** \n{2}".format(message.author.mention,
                                                                                        ticket[0],
                                                                                        closemsg)
                ticketauthor = await client.get_user_info(ticket[1])
                await client.send_message(ticketauthor, msg_to_user)

            sqlib.tickets.update(content, {'closed': 1})
            await client.send_message(message.channel, "Ticket closed.")

            channel_id = str(sqlib.servers.get(sqlib.tickets.get(content, 'server')[0], 'channel')[0])
            channel = client.get_channel(channel_id)

            if channel is None:
                await client.send_message(message.channel, "There is no support channel on the server.")
                return 0

            suppmsg = "**{0} just closed ticket #{1}**: \n{2}".format(message.author.mention, content, closemsg)

            supprole_id = sqlib.servers.get(message.server.id, 'role')[0]
            if supprole_id != '0':
                supprole = discord.utils.find(lambda r: r.id == supprole_id, message.server.roles)

                if supprole is None:
                    await client.send_message(message.channel, "It seems like the support-role doesn't exist anymore. "
                                                               ":confused:")
                    return 0
                await client.send_message(channel, supprole.mention + '\n' + suppmsg)

            else:
                await client.send_message(channel, suppmsg)

    elif message.content.lower().startswith(prefix + 'addinfo'):
        content = message.content[9:]

        if content == 'help':
            help_embed = discord.Embed(
                title='AddInfo',
                description=helpmsg['addinfo'].format(prefix=prefix),
                color=0x37ceb2
            )
            await client.send_message(message.channel, embed=help_embed)
            return 0

        ticket_nr = content.split(' ')[0]
        ticket = sqlib.tickets.get(ticket_nr)

        if ticket is None:
            await client.send_message(message.channel, "Given ticket can't be found.")
            return 0

        if ticket[5] == 1:
            await client.send_message(message.channel, "This ticket is closed.")
            return 0

        if ticket[1] != message.author.id:
            await client.send_message(message.channel, "You have to be ticket author for that.")
            return 0

        content = content.replace(ticket_nr, '')

        title = time.strftime('%d.%m.%y %H:%M')
        added_dict = json.loads(ticket[4].replace("'", '"'))
        added_dict[title] = content

        channel_id = str(sqlib.servers.get(message.server.id, 'channel')[0])
        channel = client.get_channel(channel_id)

        if channel is None:
            await client.send_message(message.channel, ":hushed: I can't find the support-channel anymore.")
            return 0

        ticket_embed = discord.Embed(
            title="New information:",
            color=0x37ceb2
        )
        ticket_embed.add_field(
            name=title,
            value=content
        )

        suppmsg = "{0} just added info to ticket #{1}".format(message.author.mention, ticket_nr)

        supprole_id = sqlib.servers.get(message.server.id, 'role')
        if supprole_id is not None:
            supprole = discord.utils.find(lambda r: r.id == supprole_id[0], message.server.roles)

            if supprole is None:
                await client.send_message(message.channel, "It seems like the support-role doesn't exist anymore. "
                                                           ":confused:")
                return 0
            await client.send_message(channel, suppmsg + ', ' + supprole.mention, embed=ticket_embed)

        else:
            await client.send_message(channel, suppmsg, embed=ticket_embed)

        sqlib.tickets.update(ticket_nr, {'added': str(added_dict)})
        await client.send_message(message.channel, "Info added.")

    elif message.content.lower().startswith(prefix + "channel"):
        content = message.content[9:]

        if content == 'help':
            help_embed = discord.Embed(
                title='Channel',
                description=helpmsg['channel'].format(prefix=prefix),
                color=0x37ceb2
            )
            await client.send_message(message.channel, embed=help_embed)
            return 0

        if (not message.author.server_permissions.administrator) and (message.author.id not in bot_admins):
            await client.send_message(message.channel, "You have to be admin for that.")
            return 0

        channel_id = re.sub(r"<#(\d+)>", r"\1", content)

        if client.get_channel(channel_id) is None:
            await client.send_message(message.channel, "You have to mention the channel.")
            return 0

        sqlib.servers.update(message.server.id, {'channel': channel_id})

        try:
            await client.add_reaction(message, "✅")
        except discord.errors.Forbidden:
            pass

    elif message.content.lower().startswith(prefix + 'supprole'):
        content = message.content[10:]

        if content == 'help':
            help_embed = discord.Embed(
                title='Support role',
                description=helpmsg['supprole'].format(prefix=prefix),
                color=0x37ceb2
            )
            await client.send_message(message.channel, embed=help_embed)
            return 0

        if (not message.author.server_permissions.administrator) and (message.author.id not in bot_admins):
            await client.send_message(message.channel, "You have to be admin for that.")
            return 0

        roles = message.role_mentions

        if len(roles) == 0:
            await client.send_message(message.channel, "You have to mention the role.")
            return 0

        else:
            sqlib.servers.update(message.server.id, {'role': roles[0].id})

            try:
                await client.add_reaction(message, "✅")
            except discord.errors.Forbidden:
                pass

    elif message.content.lower().startswith(prefix + 'help'):
        content = message.content[6:]

        if content == 'help':
            help_embed = discord.Embed(
                title='Help',
                description=helpmsg['help'].format(prefix=prefix),
                color=0x37ceb2
            )
            await client.send_message(message.channel, embed=help_embed)
            return 0

        help_embed = discord.Embed(
            title="Help",
            description="All commands and how to use them.",
            color=0x37ceb2
        )

        for cmd in helpmsg:
            help_embed.add_field(
                name=cmd,
                value=helpmsg[cmd].format(prefix=prefix),
                inline=False
            )

        if message.author.server_permissions.administrator or message.author.id in bot_admins:
            destination = message.channel
        else:
            destination = message.author
            try:
                await client.add_reaction(message, "✅")
            except discord.errors.Forbidden:
                pass

        await client.send_message(destination, embed=help_embed)

    elif message.content.lower().startswith(prefix + 'prefix'):
        content = message.content[8:]

        if content == 'help':
            help_embed = discord.Embed(
                title='Prefix',
                description=helpmsg['prefix'].format(prefix=prefix),
                color=0x37ceb2
            )
            await client.send_message(message.channel, embed=help_embed)
            return 0

        if (not message.author.server_permissions.administrator) and (message.author.id not in bot_admins):
            await client.send_message(message.channel, "You have to be admin for that.")
            return 0

        if len(content) != 1:
            await client.send_message(message.channel, "The prefix has to be **one** character.")
            return 0

        sqlib.servers.update(message.server.id, {'prefix': content})

        await client.send_message(message.channel, "Okay, new prefix is `{0}`.".format(content))

    elif message.content.lower().startswith(prefix + 'invite'):
        content = message.content[8:]

        if content == 'help':
            help_embed = discord.Embed(
                title='Invite',
                description=helpmsg['invite'].format(prefix=prefix),
                color=0x37ceb2
            )
            await client.send_message(message.channel, embed=help_embed)
            return 0

        await client.send_message(
            message.channel,
            "Okay, invite me to your Server:\n"
            "https://discordapp.com/oauth2/authorize?client_id=360801859461447700&scope=bot&permissions=19456"
        )


@client.event
async def on_server_join(server):
    post_to_dbotsorg()
    if sqlib.servers.get(server.id) is None:
        sqlib.servers.add_element(server.id, {'prefix': '/'})
    try:
        await client.send_message(server.owner, "Hey, you or an admin on your server invited me to '{0}'. :smiley:\n"
                                                "The default prefix is `/`, so type `/help` into a text channel "
                                                "on the server to see what you "
                                                "(or rather I) can do.".format(server.name))

        if server.default_channel is not None:
            await client.send_message(server.default_channel, "Hey, I'm glad to be here. "
                                                              "Hopefully I'll be helpful :smiley:.\n"
                                                              "Type `/help` to see all available commands.")
    except discord.errors.Forbidden:
        pass


client.run('BOT-TOKEN')  # TODO: insert token
