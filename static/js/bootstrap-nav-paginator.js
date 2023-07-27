/*!
 * Bootstrap Nav Paginator 1.0.2
 * Author: Robin Prugne
 */

/**
 * @summary     Bootstrap Nav Paginator
 * @description Pagination module for Bootstrap's nav component
 * @version     1.0.2
 * @file        bootstrap-nav-paginator.js
 * @author      Robin Prugne
 *
 * This source file is free software, available under the following license:
 *      MIT license
 */

let navs = [], pages_index = [], n_items_per_pages = [], selectors = [];

document.addEventListener("DOMContentLoaded", function() {
    Array.from(document.querySelectorAll('.nav-paginator')).forEach(function(e,i){
        initialize(e,i);
        add_buttons(i);
        update_view(i);
        events(i);
    });
});

function initialize(e,i){
    navs[i] = e;

    if(navs[i].dataset.paginatorItemCount !== undefined){
        if(navs[i].dataset.paginatorItemCount > 0){
            n_items_per_pages[i] = navs[i].dataset.paginatorItemCount;
            pages_index[i] = get_page_from_item(i, e.tagName.toLowerCase() === "ul" ? e.querySelectorAll('.active')[0].parentNode : e.querySelectorAll('.active')[0]);
        }else{
            throw "Bootstrap Nav Paginator Error: attribute 'item count' must be a positive number.";
        }
    }else{
        throw "Bootstrap Nav Paginator Error: attribute 'item count' is missing.";
    }
}

function add_buttons(i){
    let list_item_p = document.createElement("li");
    list_item_p.classList = "nav-item p-0 py-3";
    list_item_p.innerHTML = ` 
            <a class="btn nav-paginator-prev" href="#">
                <svg aria-hidden="true" focusable="false" data-prefix="fas" data-icon="angle-double-left" class="svg-inline--fa fa-angle-double-left fa-w-14" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512" style="height: 30px;">
                    <path fill="currentColor" d="M223.7 239l136-136c9.4-9.4 24.6-9.4 33.9 0l22.6 22.6c9.4 9.4 9.4 24.6 0 33.9L319.9 256l96.4 96.4c9.4 9.4 9.4 24.6 0 33.9L393.7 409c-9.4 9.4-24.6 9.4-33.9 0l-136-136c-9.5-9.4-9.5-24.6-.1-34zm-192 34l136 136c9.4 9.4 24.6 9.4 33.9 0l22.6-22.6c9.4-9.4 9.4-24.6 0-33.9L127.9 256l96.4-96.4c9.4-9.4 9.4-24.6 0-33.9L201.7 103c-9.4-9.4-24.6-9.4-33.9 0l-136 136c-9.5 9.4-9.5 24.6-.1 34z"></path>
                </svg>
            </a>`;
    navs[i].prepend(list_item_p);

    let list_item_n = document.createElement("li");
    list_item_n.classList = "nav-item p-0 py-3";
    list_item_n.innerHTML = ` 
            <a class="btn nav-paginator-next" href="#">
                <svg aria-hidden="true" focusable="false" data-prefix="fas" data-icon="angle-double-right" class="svg-inline--fa fa-angle-double-right fa-w-14" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512" style="height: 30px;">
                    <path fill="currentColor" d="M224.3 273l-136 136c-9.4 9.4-24.6 9.4-33.9 0l-22.6-22.6c-9.4-9.4-9.4-24.6 0-33.9l96.4-96.4-96.4-96.4c-9.4-9.4-9.4-24.6 0-33.9L54.3 103c9.4-9.4 24.6-9.4 33.9 0l136 136c9.5 9.4 9.5 24.6.1 34zm192-34l-136-136c-9.4-9.4-24.6-9.4-33.9 0l-22.6 22.6c-9.4 9.4-9.4 24.6 0 33.9l96.4 96.4-96.4 96.4c-9.4 9.4-9.4 24.6 0 33.9l22.6 22.6c9.4 9.4 24.6 9.4 33.9 0l136-136c9.4-9.2 9.4-24.4 0-33.8z"></path>
                </svg>
            </a>`;
    navs[i].append(list_item_n);

    selectors[i] = [];
    selectors[i]['prev'] = list_item_p.children[0];
    selectors[i]['next'] = list_item_n.children[0];

    if(navs[i].dataset.paginatorButtonsClass !== undefined){
        if(navs[i].dataset.paginatorButtonsClass.length > 0){
            navs[i].dataset.paginatorButtonsClass.split(' ').forEach(function(c){
                selectors[i]['prev'].classList.add(c);
                selectors[i]['next'].classList.add(c);
            });
        }
    }
}

function update_view(i){
    let array_b = Array.from(navs[i].children);
    array_b = array_b.filter(e => array_b.indexOf(e) !== 0 && array_b.indexOf(e) !== navs[i].children.length-1);
    Array.from(array_b, function(e,n){
        n < n_items_per_pages[i]*pages_index[i] && n >= n_items_per_pages[i]*(pages_index[i]-1) ? e.style.display = 'block' : e.style.display = 'none';
    });

    pages_index[i] === 1 ? selectors[i]['prev'].classList.add("disabled") :  selectors[i]['prev'].classList.remove("disabled");
    array_b.length <= n_items_per_pages[i] * pages_index[i] ? selectors[i]['next'].classList.add("disabled") : selectors[i]['next'].classList.remove("disabled");
}

function events(i){
    selectors[i]['next'].addEventListener("click", function(){
        pages_index[i]++;
        update_view(i);
    });

    selectors[i]['prev'].addEventListener("click", function(){
        pages_index[i]--;
        update_view(i);
    });
}

function get_page_from_item(i, item){
    let all_items = Array.prototype.slice.call(navs[i].children);
    let item_index = all_items.indexOf(item);
    return parseInt(item_index/n_items_per_pages[i])+1;
}

//prototype function
Element.prototype.BsNavPaginator = function(item_count, buttons_class = "") {
    let i = navs.length;

    this.dataset.paginatorItemCount = item_count;
    this.dataset.paginatorButtonsClass = buttons_class;

    initialize(this,i);
    add_buttons(i);
    update_view(i);
    events(i);
}