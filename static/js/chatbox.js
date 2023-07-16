(function(){
  
  var chat = {
    messageToSend: '',
    messageResponses: [
      'Why did the web developer leave the restaurant? Because of the table layout.',
      'How do you comfort a JavaScript bug? You console it.',
      'An SQL query enters a bar, approaches two tables and asks: "May I join you?"',
      'What is the most used language in programming? Profanity.',
      'What is the object-oriented way to become wealthy? Inheritance.',
      'An SEO expert walks into a bar, bars, pub, tavern, public house, Irish pub, drinks, beer, alcohol'
    ],
    init: function() {
      this.cacheDOM();
      this.bindEvents();
      this.render();
    },
    cacheDOM: function() {
      this.$chatHistory = $('.chat-history');
      this.$button = $('button');
      this.$textarea = $('#message-to-send');
      this.$chatHistoryList =  this.$chatHistory.find('ul');
      this.$spinnerBlock = $('#spinner-block');
      this.$sampleQuestions = $('#sample-questions')
    },
    bindEvents: function() {
      this.$button.on('click', this.addMessage.bind(this));
      this.$textarea.on('keyup', this.addMessageEnter.bind(this));
      this.$sampleQuestions.on('click', 'a', this.askQuestion.bind(this));
    },
    render: function() {   
      this.scrollToBottom();
      if (this.messageToSend.trim() !== '') {     
        var template = Handlebars.compile($("#message-template").html());
        var context = { 
          messageOutput: this.messageToSend,
          time: this.getCurrentTime()
        };

        this.$chatHistoryList.append(template(context));
        this.scrollToBottom();
        this.$textarea.val('');   
        
        //show the spinner now
        this.$chatHistoryList.append(this.$spinnerBlock.clone().show());
        
        // responses
        var templateResponse = Handlebars.compile( $("#message-response-template").html());
        var contextResponse = { 
          // response: this.getRandomItem(this.messageResponses),
          response: 'you entered ' + this.messageToSend,
          time: this.getCurrentTime()
        };    
        
        setTimeout(function() {
          //remove the spinner block
          this.$chatHistoryList.find('li').last().remove();
          this.$chatHistoryList.append(templateResponse(contextResponse));
          this.scrollToBottom();
        }.bind(this), 1500);        
        
      }
      
    },
    
    addMessage: function() {
      this.messageToSend = this.$textarea.val()
      this.render();         
    },
    addMessageEnter: function(event) {
        // enter was pressed
        if (event.keyCode === 13) {
          this.addMessage();
        }
    },
    scrollToBottom: function() {
       this.$chatHistory.scrollTop(this.$chatHistory[0].scrollHeight);
    },
    getCurrentTime: function() {
      return new Date().toLocaleTimeString().
              replace(/([\d]+:[\d]{2})(:[\d]{2})(.*)/, "$1$3");
    },
    getRandomItem: function(arr) {
      return arr[Math.floor(Math.random()*arr.length)];
    },
    askQuestion: function(event) {
      event.preventDefault();
      var $target = $(event.target);      
      console.log($target.text())
      this.messageToSend = $target.text();
      this.render();  
    },

    
  };
  
  chat.init();
  
  // var searchFilter = {
  //   options: { valueNames: ['name'] },
  //   init: function() {
  //     var userList = new List('people-list', this.options);
  //     var noItems = $('<li id="no-items-found">No items found</li>');
      
  //     userList.on('updated', function(list) {
  //       if (list.matchingItems.length === 0) {
  //         $(list.list).append(noItems);
  //       } else {
  //         noItems.detach();
  //       }
  //     });
  //   }
  // };
  
  // searchFilter.init();
  
})();
