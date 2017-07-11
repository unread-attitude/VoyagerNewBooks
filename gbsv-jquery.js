/*##########################################################################
# Copyright 2008 Rector and Visitors of the University of Virginia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
##########################################################################*/

/*

A jQuery plugin for the Google Book Search Viewability API - http://code.google.com/apis/books/getting-started.html

Version: 		0.5.0
Date Modified: 		3-18-08
Author: 		Matt Mitchell - mwm4n

Recent Changes:
	Completely removed overly-complicated "span" tag scheme, in favor of working with the real HTML source.

If the bibkey (a.title or img.alt) is invalid, the element is left alone.
	For links this should always be #preview or #info
	For images, this leaves the option of having a default "src"

Example HTML
	<dt>Thumbnail</dt>
	<dd>
		<img src="default_cover.gif" class="gbsv" alt="ISBN:0743226720"/>
	</dd>
	
	<dt>Preview Link</dt>
	<dd>
		<a href="#preview" class="gbsv" title="ISBN:0743226720">Preview</a>
	</dd>
	
	<dt>Info Link</dt>
	<dd>
		<a href="#info" class="gbsv" title="ISBN:0743226720">Info</a>
	</dd>
	
	<dt>Preview Link + Thumbnail - nested img tag doesn't need bib-key</dt>
	<dd>
		<a href="#preview" class="gbsv" title="ISBN:0743226720"><img src="default_cover.gif" class="gbsv"/></a>
	</dd>
	
	<dt>Info Link + Thumbnail - nested img tag doesn't need bib-key</dt>
	<dd>
		<a href="#info" class="gbsv" title="ISBN:0743226720"><img src="default_cover.gif" class="gbsv"/></a>
	</dd>

Example Javascript
	$(function(){ $.GBSV.init() })

Notes
	Another javascript "Google Book Service Viewability" solution: libx.org/gbs

*/

jQuery.GBSV = {
	
	/* The HTL "class" prefix */
	class_name : 'gbsv',
	
	/* Base url to Google Books */
	url : 'http://books.google.com/books',
	
	/* Base query string for the initial GBS call */
	base_query : 'jscmd=viewapi&callback=jQuery.GBSV.processBookInfoResponse&bibkeys=',
	
	/*
		initializes properties, loops through each "a" and "img" tag that has a "gbsv" class
		collects the bibkey from a.title and img.alt attributes
			- the a tags must have a named anchor of either "preview" or "info"
		builds query for GBSV service request
		appends a script tag with the generated url
		populates the img.src attribute and the a.href attribute
	*/
	init : function(){
		var bibkeys = [];
		var found_elements = this.found_elements={}
		
		jQuery('a.' + this.class_name).each(function(){
			var t=jQuery(this)
			bibkeys.push(t.attr('title'));
			found_elements[t.attr('title')] = found_elements[t.attr('title')] ? found_elements[t.attr('title')] : []
			found_elements[t.attr('title')].push(t);
		});
		
		jQuery('img.' + this.class_name).each(function(){
			var t=jQuery(this);
			if(t.parent()[0].tagName=='A'){return false;}
			bibkeys.push(t.attr('alt'));
			found_elements[t.attr('alt')] = found_elements[t.attr('alt')] ? found_elements[t.attr('alt')] : []
			found_elements[t.attr('alt')].push(t);
		});
		
		this.loadFromBibKeys(bibkeys);
	},
	
	/*
		Creates the request url from the bibkeys arg, then appends a script tag using the url as the src
	*/
	loadFromBibKeys : function(bibkeys){
		jQuery('body').append('<script src=' + this.createRequestURL(bibkeys) + '/>');
	},
	
	/*
		Creates the request url using the bibkeys arg
	*/
	createRequestURL : function(bibkeys){
		return this.url + '?' + this.base_query + this.arrayUnique(bibkeys).join(',')
	},
	
	/*
		Removes duplicate values from an array
	*/
	arrayUnique : function(src_array){
		var o = new Object();
		var i, e;
		for (i = 0; e = src_array[i]; i++) {o[e] = 1};
		var a = new Array();
		for (e in o) {a.push (e)};
		return a;
	},
	
	/*
		Process the data returned from the GBSV service
		Calls handleItem for each item
	*/
	processBookInfoResponse : function(data){
		for(bibkey in this.found_elements){
			for(i in this.found_elements[bibkey]){
				this.processElement(this.found_elements[bibkey][i], data[bibkey]);
			}
		}
	},
	
	processElement : function(el, data){
		if(el[0] && el[0].tagName=='A'){
			this.processAElement(el, data);
		}
		if(el[0] && el[0].tagName=='IMG'){
			this.processImgElement(el, data);
		}
	},
	
	processAElement : function(el, data){
		var k=el.attr('href').match(/[^#]+/);
		el.attr('href', data[k + '_url']);
		// Find an img.gbsv elements that might be inside of this a tag, apply the thumbnail src
		jQuery('img.' + this.class_name, el).attr('src', data['thumbnail_url']);
	},
	
	processImgElement : function(el, data){
		if(data) el.attr('src', data['thumbnail_url']);
	}
	
}