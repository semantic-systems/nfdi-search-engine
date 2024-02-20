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
      this.is_chatbot_ready();
      this.render();
    },
    cacheDOM: function() {
      this.$chatHistory = $('.chat-history');
      this.$button = $('#btn-send-message');
      this.$textarea = $('#message-to-send');
      this.$chatHistoryList =  this.$chatHistory.find('ul');
      this.$spinnerBlock = $('#spinner-block');
      this.$sampleQuestions = $('#sample-questions');
      this.$search_uuid = $('#search_uuid')
    },
    bindEvents: function() {
      // this.$button.on('click', this.addMessage.bind(this));
      this.$button.off('click');
      this.$textarea.on('keyup', this.addMessageEnter.bind(this));
      this.$sampleQuestions.on('click', 'a', this.askSampleQuestion.bind(this));
    },
    is_chatbot_ready: function() {
      var _this=this;
      myInterval = setInterval(function() {
        $.ajax({
          url: '/are-embeddings-generated',
          type: "GET",
          data: {              
          },
          beforeSend: function () {
          },
          complete: function () {
          },              
          success: function (data) {
            console.log(data)             
            if(data == 'True'){            
              _this.$button.text('Send')
              _this.$button.on('click', _this.addMessage.bind(_this)); //bind the click event   
              clearInterval(myInterval); //cancel the execution once we know the embeddings have been generated           
            }
          },
          error: function (err) {
              console.log(err);
              return err
          }
        });        
      }.bind(_this), 3000);  
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
        
        // // responses
        // var templateResponse = Handlebars.compile( $("#message-response-template").html());
        // var contextResponse = { 
        //   // response: this.getRandomItem(this.messageResponses),          
        //   // response: 'you have asked me ' + this.messageToSend,
        //   response: this.getAnswer(),
        //   time: this.getCurrentTime()
        // };    
        
        // setTimeout(function() {
        //   //remove the spinner block
        //   this.$chatHistoryList.find('li').last().remove();
        //   this.$chatHistoryList.append(templateResponse(contextResponse));
        //   this.scrollToBottom();
        // }.bind(this), 2000);        
        
      }
      
    },
    
    addMessage: function() {
      console.log('add message')
      this.messageToSend = this.$textarea.val()
      this.render();  
      this.getAnswer();       
    },
    addMessageEnter: function(event) {
        // enter was pressed
        if (event.keyCode === 13) {
          this.addMessage();
        }
    },
    scrollToBottom: function() {
      if (this.$chatHistory[0]) {
        this.$chatHistory.scrollTop(this.$chatHistory[0].scrollHeight);
      }
    },
    getCurrentTime: function() {
      return new Date().toLocaleTimeString().
              replace(/([\d]+:[\d]{2})(:[\d]{2})(.*)/, "$1$3");
    },
    getRandomItem: function(arr) {
      return arr[Math.floor(Math.random()*arr.length)];
    },
    askSampleQuestion: function(event) {
      event.preventDefault();
      var $target = $(event.target); 
      console.log('ask Question')     
      console.log($target.text())
      this.messageToSend = $target.text();
      this.render();  
      this.getAnswer();
    },     
    getAnswer: function() {

      var _this=this;

      $.ajax({
        url: '/get-chatbot-answer',
        type: "GET",
        // async: false,
        data: {
            question: this.messageToSend
        },
        beforeSend: function () {
            // $('#publications').append("<div class='loader'><div class='sp-3balls'></div></div>");
        },
        complete: function () {
            // $('.loader').remove();
        },              
        success: function (data) {
          console.log(data)          
          // responses
          var templateResponse = Handlebars.compile( $("#message-response-template").html());
          var contextResponse = {  
            response: data,
            time: _this.getCurrentTime()
          };    

          _this.$chatHistoryList.find('li').last().remove();
          _this.$chatHistoryList.append(templateResponse(contextResponse));
          _this.scrollToBottom();

        },
        error: function (err) {
            console.log(err);
            return err
        }
      });

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
