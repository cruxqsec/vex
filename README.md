# Vex the web security toolkit that lives in your termianl

## Description
Vex is a security toolkit like Burp, Caido or Zap proxy that integrates all the main features in the terminal.
It is keyboard driven tool that utilizes vim keybindings and enables security researchers to speed up their research.
This tool is still under development and many things may change.

## Structure
1. vex - client Terminal app built with Textual

2. vex-cli - backend component that builds uppon mitmproxy and adds API endpoints and websockets to it

## TODO

### vex client
* improve startup logic

* implement history screen
1. start websockets when a project is selected
2. save in temporary cache the recieved requests
3. get all summaries in an effiecient way
4. imrove history layout (request/response pair can be maximized)
5. responsivness

### vex-cli
* implement scope functionality
1. ability to add simple scopes (domains, ips, ipv6)
2. ability to toggle scopes on and off
3. add regex support and wildcard domains (*.google.com)

* implement replay functionality
1. add the ability to replay a request
2. save the new replays into a database and track changes

* implement intercept functionality
1. implement the ability to pause requests
2. implement the ability for any client to forward/drop
3. implement the ability to pause recieved responses

* improve performance
1. deleting the cached responses from mitmproxy
2. better database optimizations (indexing)

* improve API
1. pagination, limit support for getting all objects
2. improve naming API scheme
3. add functionality (delete all,...)



