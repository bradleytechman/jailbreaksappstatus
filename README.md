# jailbreaks.app status bot

a discord bot to check the status of [jailbreaks.app](https://jailbreaks.app) 

The official instance to be added to servers is at https://discord.com/oauth2/authorize?client_id=1369857399313268886&permissions=216064&integration_type=0&scope=bot+applications.commands

## features

* `/status` - shows current jailbreaks.app signing status
* `/certinfo` - shows current certificate info
* `/configure` - allows server admins/added users to post status updates when the status changes
* can post a message in a channel and ping a role when signed/unsigned (checks once a minute)
* can show a note in the `/status` message (eg: globally blacklisted but signed)

## setup

1. Go to https://discord.com/developers/applications
2. Press New Application
3. Name it, make a team if you want, create
4. i'll finish the rest later but you can probabaly figure it out for making a bot
5. run `curl -sSL https://raw.githubusercontent.com/bradleytechman/jailbreaksappstatus/refs/heads/main/setup.sh | bash`

* this was made with chatgpt
* The old commits used to be there but I accidentally got rid of them
