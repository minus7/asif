# Adopted from InspIRCd
# https://github.com/inspircd/inspircd/blob/master/include/numerics.h

RPL_WELCOME                     = "001"  # 2812, not 1459
RPL_YOURHOSTIS                  = "002"  # 2812, not 1459
RPL_SERVERCREATED               = "003"  # 2812, not 1459
RPL_SERVERVERSION               = "004"  # 2812, not 1459
RPL_ISUPPORT                    = "005"  # not RFC, extremely common though (defined as RPL_BOUNCE in 2812, widely ignored)

RPL_MAP                         = "006"  # unrealircd
RPL_ENDMAP                      = "007"  # unrealircd
RPL_SNOMASKIS                   = "008"  # unrealircd
RPL_REDIR                       = "010"

RPL_YOURUUID                    = "042"  # taken from ircnet

RPL_UMODEIS                     = "221"
RPL_RULES                       = "232"  # unrealircd

RPL_LUSERCLIENT                 = "251"
RPL_LUSEROP                     = "252"
RPL_LUSERUNKNOWN                = "253"
RPL_LUSERCHANNELS               = "254"
RPL_LUSERME                     = "255"

RPL_ADMINME                     = "256"
RPL_ADMINLOC1                   = "257"
RPL_ADMINLOC2                   = "258"
RPL_ADMINEMAIL                  = "259"

RPL_LOCALUSERS                  = "265"
RPL_GLOBALUSERS                 = "266"

RPL_MAPUSERS                    = "270"  # insp-specific

RPL_AWAY                        = "301"

RPL_SYNTAX                      = "304"  # insp-specific

RPL_UNAWAY                      = "305"
RPL_NOWAWAY                     = "306"

RPL_RULESTART                   = "308"  # unrealircd
RPL_RULESEND                    = "309"  # unrealircd

RPL_WHOISSERVER                 = "312"
RPL_WHOWASUSER                  = "314"

RPL_ENDOFWHO                    = "315"
RPL_ENDOFWHOIS                  = "318"

RPL_LISTSTART                   = "321"
RPL_LIST                        = "322"
RPL_LISTEND                     = "323"

RPL_CHANNELMODEIS               = "324"
RPL_CHANNELCREATED              = "329"  # ???
RPL_NOTOPICSET                  = "331"
RPL_TOPIC                       = "332"
RPL_TOPICTIME                   = "333"  # not RFC, extremely common though

RPL_INVITING                    = "341"
RPL_INVITELIST                  = "346"  # insp-specific (stolen from ircu)
RPL_ENDOFINVITELIST             = "347"  # insp-specific (stolen from ircu)
RPL_VERSION                     = "351"
RPL_NAMREPLY                    = "353"
RPL_LINKS                       = "364"
RPL_ENDOFLINKS                  = "365"
RPL_ENDOFNAMES                  = "366"
RPL_ENDOFWHOWAS                 = "369"

RPL_INFO                        = "371"
RPL_ENDOFINFO                   = "374"
RPL_MOTD                        = "372"
RPL_MOTDSTART                   = "375"
RPL_ENDOFMOTD                   = "376"

RPL_WHOWASIP                    = "379"

RPL_YOUAREOPER                  = "381"
RPL_REHASHING                   = "382"
RPL_TIME                        = "391"
RPL_YOURDISPLAYEDHOST           = "396"  # from charybdis/etc, common convention

# Error range of numerics
ERR_NOSUCHNICK                  = "401"
ERR_NOSUCHSERVER                = "402"
ERR_NOSUCHCHANNEL               = "403"  # used to indicate an invalid channel name also, so don't rely on RFC text (don't do that anyway!)
ERR_CANNOTSENDTOCHAN            = "404"
ERR_TOOMANYCHANNELS             = "405"
ERR_WASNOSUCHNICK               = "406"
ERR_INVALIDCAPSUBCOMMAND        = "410"  # ratbox/charybdis(?)
ERR_NOTEXTTOSEND                = "412"
ERR_UNKNOWNCOMMAND              = "421"
ERR_NOMOTD                      = "422"
ERR_ERRONEUSNICKNAME            = "432"
ERR_NICKNAMEINUSE               = "433"
ERR_NORULES                     = "434"  # unrealircd
ERR_USERNOTINCHANNEL            = "441"
ERR_NOTONCHANNEL                = "442"
ERR_USERONCHANNEL               = "443"
ERR_CANTCHANGENICK              = "447"  # unrealircd, probably
ERR_NOTREGISTERED               = "451"
ERR_NEEDMOREPARAMS              = "461"
ERR_ALREADYREGISTERED           = "462"
ERR_YOUREBANNEDCREEP            = "465"
ERR_UNKNOWNMODE                 = "472"

ERR_BADCHANNELKEY               = "475"
ERR_INVITEONLYCHAN              = "473"
ERR_CHANNELISFULL               = "471"
ERR_BANNEDFROMCHAN              = "474"

ERR_BANLISTFULL                 = "478"

ERR_NOPRIVILEGES                = "481"  # rfc, beware though, we use this for other things opers may not do also
ERR_CHANOPRIVSNEEDED            = "482"  # rfc, beware though, we use this for other things like trying to kick a uline

ERR_RESTRICTED                  = "484"

ERR_ALLMUSTSSL                  = "490"  # unrealircd
ERR_NOOPERHOST                  = "491"
ERR_NOCTCPALLOWED               = "492"  # XXX: bzzzz. 1459 defines this as ERR_NOSERVICEHOST, research it more and perhaps change this! (ERR_CANNOTSENDTOCHAN?)
                                        # wtf, we also use this for m_noinvite. UGLY!
ERR_DELAYREJOIN                 = "495"  # insp-specific, XXX: we should use 'resource temporarily unavailable' from ircnet/ratbox or whatever
ERR_UNKNOWNSNOMASK              = "501"  # insp-specific
ERR_USERSDONTMATCH              = "502"
ERR_CANTJOINOPERSONLY           = "520"  # unrealircd, but crap to have so many numerics for cant join..
ERR_CANTSENDTOUSER              = "531"  # ???

RPL_COMMANDS                    = "702"  # insp-specific
RPL_COMMANDSEND                 = "703"  # insp-specific

ERR_CHANOPEN                    = "713"
ERR_KNOCKONCHAN                 = "714"

ERR_WORDFILTERED                = "936"  # insp-specific, would be nice if we could get rid of this..
ERR_CANTUNLOADMODULE            = "972"  # insp-specific
RPL_UNLOADEDMODULE              = "973"  # insp-specific
ERR_CANTLOADMODULE              = "974"  # insp-specific
RPL_LOADEDMODULE                = "975"  # insp-specific

# String commands, for convenience
NICK                            = "NICK"
USER                            = "USER"
JOIN                            = "JOIN"
PART                            = "PART"
QUIT                            = "QUIT"
MODE                            = "MODE"
PING                            = "PING"
PONG                            = "PONG"
PRIVMSG                         = "PRIVMSG"
NOTICE                          = "NOTICE"
TOPIC                           = "TOPIC"
KICK                            = "KICK"
INVITE                          = "INVITE"
PASS                            = "PASS"
