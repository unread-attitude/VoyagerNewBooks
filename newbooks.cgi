#!/m1/shared/bin/perl

###############################################################################
#                                                                             #
#  New Books List, Version 7.3 for Unix                                       #
#                                                                             #
#  newBooks.cgi for 'vwebv' version of WebVoyage                              #
#                                                                             #
#  Michael Doran, doran@uta.edu                                               #
#                                                                             #
#  University of Texas at Arlington Libraries                                 #
#  Box 19497, Arlington, TX 76019, USA                                        #
#                                                                             #
#  More information at: http://rocky.uta.edu/doran/newbooks/                  #
#                                                                             #
#  2017-04-13 Includes ELG cloud patch by James R Mitchell (Thanks! //mdd)    #
#                                                                             #
###############################################################################
#                                                                             #
#  Copyright 2000-2017, The University of Texas at Arlington ("UTA").         #
#  All rights reserved.  See included LICENSE for particulars.                #
#                                                                             #
###############################################################################

use strict;
use Encode;
use Unicode::Normalize;
use Socket qw(inet_ntoa);
# Note: LWP::UserAgent also used

use lib '../../newbooks';

my $version     = "7.3 for Unix";
my $this_script = "/vwebv/newBooks.cgi";
my $data_stream = '';
my %formdata;

our ($base_URL, $lwp_opts)  = GetBaseURL();

# y => yes, n => no, t => time
my $debug           = "n";
my $error_out_count = 0;

my $start_time = time();

#  Declare these variables prior to ReadParse
my @checked_records = ();

#  Read and parse incoming form data
ReadParse();

##########################################################
#  Assign form data to variables.
##########################################################

my $display_list  = decode('UTF-8',$formdata{'list'});
my $sort_criteria = decode('UTF-8',$formdata{'sort'});
my $search_term   = decode('UTF-8',$formdata{'text'});
my $date_range    = decode('UTF-8',$formdata{'week'});
my $recs_per_page = decode('UTF-8',$formdata{'rppg'});
my $starting_pnt  = decode('UTF-8',$formdata{'stpt'});
my $which_submit  = decode('UTF-8',$formdata{'submit'});
my $which_form    = decode('UTF-8',$formdata{'form'});
my $mail_address  = decode('UTF-8',$formdata{'address'});
my $mail_subject  = decode('UTF-8',$formdata{'emailsubj'});
my $mail_body     = decode('UTF-8',$formdata{'emailbody'});
my $which_records = decode('UTF-8',$formdata{'sels'});
my $prev_query    = decode('UTF-8',$formdata{'qstr'});
my $skin          = decode('UTF-8',$formdata{'sk'});


# Normalize: Unicode Normalization Form D (canonical decomposition) 
# i.e. decompose any precomposed accented characters
$search_term  = NFD($search_term);
# process the 'search_term' string into discreet tokens
my @search_tokens   = ();
my $iteration    = '';
my $temp_term    = $search_term;
while ($temp_term) {
    # Unicode begin/end quotes
    if ($temp_term =~ s/\p{Pi}([\P{Pi}\P{Pf}]*)\p{Pf}// ) {
        # add phrase
        push(@search_tokens, $1); 
    # ASCII double quotes
    } elsif ($temp_term =~ s/"([^"]+?)"// ) {
        # add phrase
        push(@search_tokens, $1); 
    # Non-quoted term
    } elsif ($temp_term =~ s/^([^"\p{Pi}\s]+)// ) {
        # add term
        push(@search_tokens, $1); 
    # Remove orphan double quotes
    } else {
        $temp_term =~ s/^["\p{Pi}\p{Pf}]+//;
    }
    # Clean up whitespace 
    $temp_term =~ s/^\s+//;
    $temp_term =~ s/\s+$//;
    $temp_term =~ s/\s{2,}/ /g;
    # Limit loop in case there is some strange input
    if ($iteration >= 20) {
        last;
    }
    $iteration++;
}

##########################################################
#  Create additional needed variables.
##########################################################

my $ending_pnt      = $starting_pnt + $recs_per_page - 1;
my $new_start_pnt   = $ending_pnt + 1;
my $display_count   = $starting_pnt;
my $total_count     = 1;
my %index           = ();
my @html            = ();
my @print           = ();
my $row_class       = "";

# Read in base configuration file
require "newBooks.ini";

# Determine skin
if (! $skin) {
    if ($NewBooksIni::default_skin) {
        $skin         = $NewBooksIni::default_skin;
    } else { 
        $skin         = "en_US";
    }
}

LoadLangModule($skin);

##########################################################
#  Check to see if call to script includes search input.
#  If not, return the initial search form page.
##########################################################

if ( $starting_pnt < 1 ) {
    NewSearchForm();
    exit (0);
} else {
    ReturnList();
    exit (0);
}


##########################################################
#  NewSearchForm 
##########################################################

sub NewSearchForm {
    my ($message) = @_;
    $data_stream = GetOrigDataStream("$base_URL/vwebv/searchBasic?sk=$skin");
    $data_stream = MungeAll($data_stream);
    $data_stream = MungeSearch($data_stream,$message);
    # Regurgitate the munged data
    print "Content-Type: text/html; charset=utf-8\n\n";
    print $data_stream;
    exit(0);
}


##########################################################
#  ReturnList 
##########################################################

sub ReturnList {
    $data_stream = GetOrigDataStream("$base_URL/vwebv/searchBasic?sk=$skin");
    DoSearch();
    $data_stream = MungeAll($data_stream);
    $data_stream = MungeList($data_stream);
    # Regurgitate the munged data
    print "Content-Type: text/html; charset=utf-8\n\n";
    print $data_stream;
}


##########################################################
#  LoadLangModule
##########################################################

sub LoadLangModule {
    my ($skin) = @_;
    if ($skin =~ /\s/) {
        ErrorOutput("fatal", "Skin value has whitespace.");
    }
    foreach my $skin_dir (keys (%NewBooksIni::language_modules)) { 
        if ($skin eq $skin_dir) {
            require "$NewBooksIni::language_modules{$skin_dir}";
            return;
        }
    }
}


##########################################################
#  GetBaseURL
##########################################################

sub GetBaseURL {
    my $base_URL = '';
    my $opts = undef;
    if ($ENV{'SERVER_PROTOCOL'} && $ENV{'HTTP_HOST'}) {
        my $http_protocol =  $ENV{'SERVER_PROTOCOL'}; 
        $http_protocol    =~ s#(https*)/.*#$1#i;
        $base_URL         =  $http_protocol . "://" .  $ENV{'HTTP_HOST'}; 
        if ( ( $http_protocol eq 'http'  && $ENV{'SERVER_PORT'} =~ /\S/ && $ENV{'SERVER_PORT'} != 80) ||
             ( $http_protocol eq 'https' && $ENV{'SERVER_PORT'} =~ /\S/ && $ENV{'SERVER_PORT'} != 443) ) {
             $base_URL .= $ENV{'SERVER_PORT'};
        }
        if (exists($ENV{'SERVER_ADDR'}) && $ENV{'SERVER_ADDR'} =~ /\S/ && exists($ENV{'SERVER_PORT'}) && $ENV{'SERVER_PORT'} =~ /^\d+$/) {
          my $dest_addr_p = gethostbyname($ENV{'HTTP_HOST'});
          my $dest_addr   = inet_ntoa($dest_addr_p);
          if ($dest_addr ne $ENV{'SERVER_ADDR'}) {
            $opts = ['PeerAddr' => $ENV{'SERVER_ADDR'}, 'PeerPort' => $ENV{'SERVER_PORT'}]
          }
        }

   
    } else {
        ErrorOutput('fatal', "\nRunning $0 from the command line?\n"); 
    }
    return ($base_URL, $opts);
}



sub DebugIt {
    my ($rlEntry) = @_;
    my $print_this = $rlEntry->[1];
    print "Content-Type: text/html; charset=utf-8\n\n";
    print "Printing... $print_this" . "\n";
    exit(2);
}


##########################################################
#  MungeAll
##########################################################

sub MungeAll {
    my ($data_stream) = @_;
    my $css_file    = qq(  <style media="screen,print" type="text/css">\@import "ui/$skin/css/newBooks.css";</style>
    );
    #  This "touch" localizes the vwebv session to the user's browser
    #  and is necessary when using non-default skins.
    #  This quick-and-dirty hack only good for IE7 & FireFox 2
    my $touch_script = qq(
    <script type="text/javascript">
      function touch() {
        var req = new XMLHttpRequest();
        req.open("HEAD", "$base_URL/vwebv/searchBasic?sk=$skin", true);
        req.send(null);
      };
    </script>
    );
    #######################################################################
    # Replace page title
    #######################################################################
    my $meta_data = MetaData();
    $data_stream =~ s#<title>.*</title>#<title>$Lang::page_title</title>$meta_data#g;
    $data_stream =~ s#(<h1 id="pageHeadingTitle">).*?(</h1>)#$1$Lang::page_title$2#g;
    #######################################################################
    # Replace help page link with New Books Search help page
    #######################################################################
    $data_stream =~ s#(/htdocs/help/).*?html#$1${NewBooksIni::help_page}#g;
    #######################################################################
    # Replace body tag "onfocus" 
    #######################################################################
    $data_stream =~ s#page.searchBasic#page.newBooks#g;
    #######################################################################
    # Remove "Search History" link, since it's not apropos for the New Books
    #######################################################################
    $data_stream =~ s#<a title="[\w]*?" href="searchHistory">[\w]*?</a>##ig;
    $data_stream =~ s#<a href="searchHistory">[\w\s]*?</a>##g;
    #######################################################################
    # Add touch function to body onLoad 
    #######################################################################
    $data_stream =~ s# onLoad="# onLoad="touch();#i;
    #######################################################################
    # Add New Books List css and javascript to head 
    #######################################################################
    $data_stream =~ s#</head>#$css_file$touch_script</head>#i;
    return $data_stream;
}


##########################################################
#  MungeSearch
##########################################################

sub MungeSearch {
    my ($data_stream, $message) = @_;
    my $search_form_html = SearchFormHTML();

    #######################################################################
    # If message, insert near top 
    #######################################################################
    $data_stream =~ s#(<div id="mainContent">)#$1$message#i;
    #######################################################################
    # Replace page title
    #######################################################################
    $data_stream =~ s#(<h1 id="pageHeadingTitle">).*?(</h1>)#$1$Lang::page_title$2#g;
    #######################################################################
    # Turn off 'searchBasic' tab
    $data_stream =~ s#(<li .*?) id="on">#$1 id="off">#ig;
    # For Voyager 7.2 and later
    $data_stream =~ s#(<li .*?) class="on">#$1 class="off">#ig;
    #######################################################################
    # Turn on 'New Books'  tab
    $data_stream =~ s#($Lang::tab_title.*?) id="off"#$1 id="on"#ig;
    # For Voyager 7.2 and later
    $data_stream =~ s#($Lang::tab_title.*?) class="off"#$1 class="on"#ig;
#    $data_stream =~ s# id="off" ($Lang::tab_title.*?)# id="on" $1>#ig;
    #######################################################################
    # Replace help page link with New Books Search help page
    #######################################################################
    $data_stream =~ s#(/htdocs/help/).*?html#$1${NewBooksIni::help_page}#g;
    #######################################################################
    # Replace 'searchBasic' form with New Books Search form
    #######################################################################
    $data_stream =~ s#<form .*?searchBasic.*?</form>#$search_form_html#is;
    $data_stream =~ s#(<div class="searchTip">).*?(</div>)#$1$Lang::search_tips$2#is;
    #######################################################################
    # Edit "pageInputFocus"
    #######################################################################
    $data_stream =~ s#page.searchBasic#page.newBooks#gi;
    #######################################################################
    # Edit "pageInputFocus"
    #######################################################################
    return $data_stream;
}


##########################################################
#  MungeList
##########################################################

sub MungeList {
    my ($data_stream) = @_;
    #######################################################################
    # Replace page title
    #######################################################################
    $data_stream =~ s#(<h1 id="pageHeadingTitle">).*?(</h1>)#$1$Lang::page_title$2#g;
    #######################################################################
    # Turn the "Search" tab off
    #######################################################################
    $data_stream =~ s#(<li title=".*?" class=")on#$1off#gi;
    #######################################################################
    # Remove 'searchBasic' form and replace with results
    #######################################################################
    $data_stream =~ s#(<div id="mainContent">).*(<div id="pageFooter">)#$1@html</div>$2#is;
    #######################################################################
    #  Replace search page css with results page css 
    #######################################################################
    $data_stream =~ s#/css/searchPages.css#/css/resultsFacets.css#gi;
    $data_stream =~ s#/css/searchBasic.css#/css/resultsTitles.css#gi;
    my $highlight_css = qq(
    <style media="screen,print" type="text/css">\@import "ui/$skin/css/highlight.css";</style>);
    $data_stream =~ s#(</style>)#$1$highlight_css#;
    return $data_stream;
}


##########################################################
#  MungeList
##########################################################

sub MungeEmailForm {
    my ($data_stream,$message) = @_;
    my $input_checked = '';
    my $email_form_css = qq(
    <style media="screen,print" type="text/css">\@import "ui/$skin/css/commonForm.css";</style>);
    if (@checked_records) {
        for my $i (@checked_records) {
            $input_checked .= qq(<input type="hidden" name="check" value="$i">
          );
        }
    }
    if ($message) {
        $message = qq(<p class="pageErrorText">$message</p>);
    }
    if (! $mail_subject) {
        $mail_subject = $Lang::this_service;
    }
    my $query_string = "$ENV{'QUERY_STRING'}";
    $query_string =~ s/submit=.*?\&//;
    $query_string =~ s/resortjump=.*?\&//;
    $query_string =~ s/check=[\d]*?\&//g;
    my $email_form_html = qq(
        <h1 id="pageHeadingTitle">$Lang::sb_email_button</h1>
         $message
        <form class="formBackround" action="$this_script" method="POST" id="eMailDialogForm">
          $input_checked 
          <input type="hidden" name="list" value="$display_list">
          <input type="hidden" name="sort" value="$sort_criteria">
          <input type="hidden" name="text" value="$search_term">
          <input type="hidden" name="week" value="$date_range">
          <input type="hidden" name="rppg" value="$recs_per_page">
          <input type="hidden" name="stpt" value="$starting_pnt">
          <input type="hidden" name="sels" value="$which_records">
          <input type="hidden" name="sk"   value="$skin">
          <input type="hidden" name="form" value="email">
          <input type="hidden" name="qstr" value="$query_string">
          <div class="formTextPair">
            <label>$Lang::email_form_to</label><input name="address" class="inputStyle" accesskey="s" type="text" value="$mail_address">
          </div>
          <div class="formTextPair">
            <label>$Lang::email_form_subject</label><input name="emailsubj" class="inputStyle" value="$mail_subject" type="text">
          </div>
          <div class="formTextPair">
            <label>$Lang::email_form_text</label><textarea name="emailbody" class="inputStyle">$mail_body</textarea>
          </div>
          <div class="formButtons">
            <input class="btn" name="submit" value="$Lang::sb_email_button" type="submit">
          </div>
        </form>
    );
    #######################################################################
    #  Replace search page css with results page css 
    #######################################################################
    $data_stream =~ s#/css/searchPages.css#/css/commonForm.css#i;
    $data_stream =~ s#/css/searchBasic.css##i;
    #######################################################################
    # Turn the "Search" tab off
    #######################################################################
    $data_stream =~ s#(<li title=".*?" class=")on#$1off#gi;
    #######################################################################
    # Remove 'searchBasic' form and replace with E-mail form
    #######################################################################
    $data_stream =~ s#(<div id="mainContent">).*(<div id="pageFooter">)#$1$email_form_html</div>$2#is;
   return $data_stream;
}


##########################################################
#  DoSearch 
##########################################################

sub DoSearch {
    my $results = '';
    my $flat_file_db = "../../newbooks/newBooks.txt";
    # Turn the locations list into an associative array
    my %locations = @NewBooksIni::locations;
    # Now match the user requested location against the
    # keys in order to assign the display name to the
    # library variable.
    my $library = $Lang::all_locations_text;
    foreach my $key (keys (%locations)) {
        if ($key eq $display_list) {
            $library = $locations{$key};
        }
    }

    # Open the flat-file database of new books
    open (DB, "$flat_file_db") || die "Can't open file: $!.\n";
    while (my $line = <DB>) {
        chomp ($line);
        my ($bib_id, $isbn, $bib_format, $author, $title, $edition, $imprint, $location, $location_temp, $dispcallno, $callno, $week) = split(/\t/, $line);
        $bib_id        = decode('UTF-8', $bib_id);
        $isbn          = decode('UTF-8', $isbn);
        $bib_format    = decode('UTF-8', $bib_format);
        $author        = decode('UTF-8', $author);
        $title         = decode('UTF-8', $title);
        $edition       = decode('UTF-8', $edition);
        $imprint       = decode('UTF-8', $imprint);
        $location      = decode('UTF-8', $location);
        $location_temp = decode('UTF-8', $location_temp);
        $dispcallno    = decode('UTF-8', $dispcallno);
        $callno        = decode('UTF-8', $callno);
        $week          = decode('UTF-8', $week);
        # Normalize: Unicode Normalization Form D (canonical decomposition) 
        # i.e. decompose any precomposed accented characters
        $title  = NFD($title);
        $author = NFD($author);
        if ( $week <= $date_range ) {
            PopulateIndex($sort_criteria, $bib_id, $author, $title, $edition, $imprint, $location, $location_temp, $dispcallno, $callno, $bib_format, $isbn)
 if $title;
        }
    }
    close (DB);

    my @sorted = sort {lc $a cmp lc $b} (keys %index);

    #  The code below fixes the 'problem' of In Process items showing up
    #  at the top of a call number sort, and items with no authors showing
    #  up at the top of an author search.  Although the DB may contain
    #  many items of either case, it will show up only once in the
    #  @sorted array.  "In Process" will be the first element because
    #  we added a space to the beginning of that field when we created
    #  it in newbooks.pl.  Records with no authors will be the first
    #  element because it has a null value.

    my $first_element = $sorted[0];
    if ($first_element =~ /In Process/i ||
        $first_element eq "" ) {
        shift(@sorted);
        push (@sorted,$first_element);
    }

    foreach my $sortkey (@sorted) {
      foreach my $rlEntry (@{$index{$sortkey}}) {
          if ($rlEntry->[5] =~ /$display_list/i) {
              ListIt($rlEntry);
          } elsif ($display_list eq 'all') {
              ListIt($rlEntry);
          }
      }
    }

    if ( $which_submit =~ /$Lang::sb_print_button/i ) {
        OutputFormat();
    } elsif ( $which_submit =~ /$Lang::sb_email_button/i ) {
        if ($which_form eq 'email') {
            SendEmail();
        } elsif ( ! @print ) {
            EmailForm("$Lang::msg_none_selected");
        } else {
            EmailForm();
        }
    } elsif ( $which_submit =~ /Edit/i ) {
        NewSearchForm();
    } else {
        if ( ! @html ) {
            NewSearchForm(qq(<p class="noHitsError">$Lang::msg_no_results</p>));
        } else {
            ListStartHTML($library, $sort_criteria);
            ListEndHTML();
        }
    }

}


##########################################################
#  OutputFormat
##########################################################
#
#  Formats & outputs records for save search results

sub OutputFormat {
    if (! @print) {
        @print = (qq(
$Lang::sb_print_button: $Lang::msg_none_selected
        ));
    };
    my $this_service = encode_utf8($Lang::this_service);
    @print = (qq(Content-Type: text/plain; charset=utf-8

$this_service
), @print,

$Lang::org_info
);

   print  @print;
   exit(0);
}


##########################################################
#  EmailForm
##########################################################

sub EmailForm {
    my ($message) = @_;
    $data_stream = GetOrigDataStream("$base_URL/vwebv/searchBasic?sk=$skin");
    $data_stream = MungeAll($data_stream);
    $data_stream = MungeEmailForm($data_stream,$message);
    # Regurgitate the munged data
    print "Content-Type: text/html; charset=utf-8\n\n";
    print $data_stream;
    exit(0);
}


##########################################################
#  SendEmail
##########################################################

sub SendEmail {
    if ( ! $mail_address ) {
        MailAck("noaddress");
    }
    # Look for valid email address
    # ...first take out any spaces
    $mail_address =~ s/ //g;
    # ...then check for valid characters
    unless ( $mail_address =~ /^\w{1}[\w\-\.]*\@[\w\-\.]+/ ) {
        # if "bad" default to print/save option
        MailAck("faulty");
    }
    # The MIME encoding allows for non-ASCII characters in the subject line
    $mail_subject = encode('MIME-Q', $mail_subject);
    my $mailprog = qq(/usr/lib/sendmail -t);
    open (MAIL, qq(| $mailprog))     || MailAck("error");
    
        if (! @print) {
        @print = (qq(

$Lang::sb_print_button: $Lang::msg_none_selected
        ));
    };
    @print = (qq(From: $Lang::email_reply_to_address
To: $mail_address
Reply-to: $Lang::email_reply_to_address
Subject: $mail_subject
Content-Type: text/plain; charset=UTF-8
MIME-Version: 1.0

$Lang::this_service

$mail_body
), @print,

$Lang::org_info
);

    print MAIL  @print;
    close (MAIL);
    MailAck();
}


##########################################################
#  MaikAck
##########################################################
#
#  Includes an acknowledgement of having sent an email

sub MailAck {
    my $status = $_[0];
    if ($status eq "noaddress") {
        EmailForm("$Lang::msg_email_err: $Lang::msg_email_err_noaddr");
    } elsif ($status eq "faulty") {
        EmailForm("$Lang::msg_email_err: $Lang::msg_email_err_faulty");
    } elsif ($status eq "error") {
        EmailForm("$Lang::msg_email_err: $Lang::msg_email_err_prog");
        warn "Mail program can't be opened.\n";
    } else {
        $which_submit = "";
        my %locations = @NewBooksIni::locations;
        my $library = $Lang::all_locations_text;
        foreach my $key (keys (%locations)) {
            if ($key eq $display_list) {
                $library = $locations{$key};
            }
        }
        ListStartHTML($library, $sort_criteria);
        ListEndHTML();
    }

}


##########################################################
#  ListIt
##########################################################
#
#  The entries that have made it this far have already
#  passed through filters for date range and location, and
#  have been sorted.  Now they are further winnowed
#  depending on what page of the results we are at and
#  if a search term was entered, here is where that is
#  looked for in the record.

sub ListIt {
    my ($rlEntry) = @_;
    #  0 $bib_id
    my $bib_id        = $rlEntry->[0];
    #  1 $author
    my $author        = $rlEntry->[1];
    #  2 $title
    my $title         = $rlEntry->[2];
    #  3 $edition
    my $edition       = $rlEntry->[3];
    #  4 $imprint
    my $imprint       = $rlEntry->[4];
    #  5 $location
    my $location      = $rlEntry->[5];
    #  6 $location_temp
    my $location_temp = $rlEntry->[6];
    #  7 $dispcallno
    my $dispcallno    = $rlEntry->[7];
    #  8 $callno
    my $callno        = $rlEntry->[8];
    #  9 $bib_format
    my $bib_format    = $rlEntry->[9];
    # 10 $isbn
    my $isbn          = $rlEntry->[10];
    if ($total_count >= $starting_pnt && $display_count <= $ending_pnt) {
        if ( !$search_term  ) {
            SaveForHTML($rlEntry);
            if ( $which_records ne 'allsel' ) {
                    SaveForPrint($rlEntry);
            }
            $display_count++;
        } elsif (TokenMatch($author,$title,$callno) =~ /y/i) {
            SaveForHTML($rlEntry);
            if ( $which_records ne 'allsel' ) {
                SaveForPrint($rlEntry);
            }
            $display_count++;
        }
    }
    if ( !$search_term ) {
        if ( $which_records eq 'allsel' ) {
            SaveForPrint($rlEntry);
        }
        $total_count++;
    } elsif (TokenMatch($author,$title,$callno) =~ /y/i) {
        if ( $which_records eq 'allsel' ) {
            SaveForPrint($rlEntry);
        }
        $total_count++;
    }
}


##########################################################
#  TokenMatch
##########################################################

sub TokenMatch {
    my($author,$title,$callno) = @_;
    my $match        = '';
    my $relevance    = '';
    my $author_strip = $author;       
       $author_strip =~ s/\p{M}*//g;       
    my $title_strip  = $title;
       $title_strip  =~ s/\p{M}*//g;
    # Remove duplicate tokens from array 
    my %seen = ();
    my @uniq = ();
    foreach my $item (@search_tokens) {
        push(@uniq, $item) unless $seen{$item}++;
    }
    @search_tokens = @uniq; 
    # Iterate through the search tokens
    foreach my $token (@search_tokens) {
        my $truncate = 'N';
        my $match    = $token;
        if ($match =~ s/[\?\*]{1}$//) {
            $truncate = 'y';
        }
        my $match_strip = $match;
        $match_strip =~ s/\p{M}*//g;
        if ($truncate eq 'y') {
            if (((length $match       > 1) && $title        =~ /\b$match/i)
             || ((length $match_strip > 1) && $title_strip  =~ /\b$match_strip/i)
             || ((length $match       > 1) && $author       =~ /\b$match/i )
             || ((length $match_strip > 1) && $author_strip =~ /\b$match_strip/i)
             || $callno =~ /^$match/i ) {
                $relevance++;
             } else {
                 $match = "n";
                 return($match);
             }
        } else {
            if (((length $match       > 1) && $title        =~ /\b$match\b/i)
             || ((length $match_strip > 1) && $title_strip  =~ /\b$match_strip\b/i)
             || ((length $match       > 1) && $author       =~ /\b$match\b/i )
             || ((length $match_strip > 1) && $author_strip =~ /\b$match_strip\b/i)
             || $callno =~ /^$match/i ) {
                $relevance++;
             } else {
                 $match = "n";
                 return($match);
             }

        }
    }
    if ($relevance >= 1) {
        $match = "y";
    }
    return($match);
}


##########################################################
#  HiLiteIt
##########################################################

sub HiLiteIt {
    my($string) = @_;
    my $match        = '';
    my $string_strip = $string;       
       $string_strip =~ s/\p{M}*//g;       
    # Remove duplicate tokens from array 
    my %seen = ();
    my @uniq = ();
    foreach my $item (@search_tokens) {
        push(@uniq, $item) unless $seen{$item}++;
    }
    @search_tokens = @uniq; 
    # Iterate through the search tokens
    foreach my $token (@search_tokens) {
        my $truncate = 'N';
        my $match    = $token;
        if ($match =~ s/[\?\*]{1}$//) {
            $truncate = 'y';
        }
        my $match_strip = $match;
        $match_strip =~ s/\p{M}*//g;
        if ($truncate eq 'y') {
            $string  =~ s#\b($match)#<span class="highlight">$1</span>#ig;
        } else {
            $string  =~ s#\b($match)\b#<span class="highlight">$1</span>#ig;
        }
    }
    return($string);
}


##########################################################
#  ListStartHTML
##########################################################

sub ListStartHTML {
    my ($library, $sort_criteria) = @_;
    my $list_top_html = '';
    my $is_selected   = '';
    my $sort_criteria_label = '';
    my $last_record_count = $display_count - 1;
    my $final_total = $total_count - 1;
    my $query_string = '';
    if ($ENV{'QUERY_STRING'}) {
        $query_string = $ENV{'QUERY_STRING'};
    } elsif ($prev_query) {
        $query_string = $prev_query;
    }
    my $edit_query_string = $query_string;
    $edit_query_string =~ s/\&submit=$which_submit//;
    $edit_query_string .= "&submit=Edit";
    my $sort_callno_query_string = $query_string;
    my $sort_author_query_string = $query_string;
    my $sort_title_query_string  = $query_string;
    $sort_callno_query_string =~ s/sort=$sort_criteria/sort=callno/;
    $sort_author_query_string =~ s/sort=$sort_criteria/sort=author/;
    $sort_title_query_string  =~ s/sort=$sort_criteria/sort=title/;
    if ($sort_criteria eq 'callno') {
        $sort_criteria_label = "$Lang::sort_label_call_no"
    } elsif ($sort_criteria eq 'author') {
        $sort_criteria_label = "$Lang::sort_label_author"
    } elsif ($sort_criteria eq 'title') {
        $sort_criteria_label = "$Lang::sort_label_title"
    }
    if ($date_range ne "1") {
        $Lang::interval = $Lang::interval_plural;
    }

    my $search_added = '';
    if ( $search_term ) {
        $search_added = "($search_term)";
    }

    my $jump_bar = PrintNav();

    $list_top_html = qq(
        <h1 id="pageHeadingTitle">$Lang::this_service</h1>
        <form name="newBooks" id="newBooks" method="get" action="$this_script">
          <div class="resultsTitleForm">
            <div class="resultsHeader">
              <div class="resultsHeaderHeader">
                <span>&nbsp; $starting_pnt-$last_record_count $Lang::results_of $final_total $Lang::results_items</span>
              </div>
              <div class="searchTerms">
                <span>$library: $date_range $Lang::interval, $Lang::results_sorted_by $sort_criteria_label $search_added</span>
              </div>
              <div class="actions">
                <ul class="navbar">
                  <li>
                    <span class="yellowBtnLeft">&nbsp;</span><span class="yellowBtn"><a href="$this_script?$edit_query_string" class="yellowBtn">&nbsp; $Lang::edit_search_btn &nbsp;</a></span><span class="yellowBtnRight">&nbsp;</span>
                  </li>
                </ul>
              </div>
            </div>
            <div id="jumpBarNavTop">$jump_bar</div>
            <div id="browseHeaderTop">
              <div class="browseHeader">
                <ul>
                  <li>
                    <span class="yellowBtnLeft">&nbsp;</span><input value="$Lang::sb_print_button" type="submit" name="submit" class="yellowBtn"><span class="yellowBtnRight">&nbsp;</span><span class="horzLine">&nbsp;</span>
                  </li>
                  <li>
                    <span class="yellowBtnLeft">&nbsp;</span><input value="$Lang::sb_email_button" type="submit" name="submit" class="yellowBtn"><span class="yellowBtnRight">&nbsp;</span><span class="horzLine">&nbsp;</span>
                  </li>
                  <li>
                    <span class="yellowBtnLeft">&nbsp;</span><input value="$Lang::sb_clear_button" type="reset" name="reset" class="yellowBtn"><span class="yellowBtnRight">&nbsp;</span><span class="horzLine">&nbsp;</span>
                  </li>
                  <li>
                    <span class="endLine">&nbsp;</span>
                  </li>
                  <li>
                    <div class="selectChkBox">
                      <span class="fieldBold">$Lang::sb_select_string</span>
                      <input value="allpage" name="sels" type="checkbox" id="sels"><label for="page">$Lang::sb_all_onpage</label>
                    </div>
                  </li>
                </ul>
                <div class="browseBarSortBy">
                  <label for="sortBy">$Lang::sort_by_label</label> 
                    <select name="resortjump" class="" OnChange="location.href=newBooks.resortjump.options[selectedIndex].value" id="resortjump">);

    if ($sort_criteria eq 'callno') {
        $is_selected = 'selected';
    } else {
        $is_selected = '';
    }
    $list_top_html .= qq(
                      <option $is_selected value="$this_script?$sort_callno_query_string">$Lang::sort_label_call_no</option>);

    if ($sort_criteria eq 'author') {
        $is_selected = 'selected';
    } else {
        $is_selected = '';
    }
    $list_top_html .= qq(
                      <option $is_selected value="$this_script?$sort_author_query_string">$Lang::sort_label_author</option>);

    if ($sort_criteria eq 'title') {
        $is_selected = 'selected';
    } else {
        $is_selected = '';
    }
    $list_top_html .= qq(
                      <option $is_selected value="$this_script?$sort_title_query_string">$Lang::sort_label_title</option>
                    </select>
                </div>
              </div>
            </div>
            <div id="theResults">
              <div id="resultList">);

    @html = ($list_top_html, @html);
}


##########################################################
#  ListEndHTML
##########################################################

sub ListEndHTML {
    my $jump_bar = PrintNav();
    my $no_quotes_search_term = $search_term;
    $no_quotes_search_term =~ s/"/&quot;/g; 
    my $hidden_inputs = qq(
              <input type="hidden" name="list" value="$display_list">
              <input type="hidden" name="sort" value="$sort_criteria">
              <input type="hidden" name="text" value="$no_quotes_search_term">
              <input type="hidden" name="week" value="$date_range">
              <input type="hidden" name="rppg" value="$recs_per_page">
              <input type="hidden" name="stpt" value="$starting_pnt">
              <input type="hidden" name="sk"   value="$skin">
    );
    @html = (@html, qq(
              </div>
            </div>
            <div id="browseHeaderbottom">
              <div class="browseHeader">
                <ul>
                  <li>
                    <span class="yellowBtnLeft">&nbsp;</span><input value="$Lang::sb_print_button" type="submit" name="submit" class="yellowBtn"><span class="yellowBtnRight">&nbsp;</span><span class="horzLine">&nbsp;</span>
                  </li>
                  <li>
                    <span class="yellowBtnLeft">&nbsp;</span><input value="$Lang::sb_email_button" type="submit" name="submit" class="yellowBtn"><span class="yellowBtnRight">&nbsp;</span><span class="horzLine">&nbsp;</span>
                  </li>
                  <li>
                    <span class="yellowBtnLeft">&nbsp;</span><input value="$Lang::sb_clear_button" type="reset" name="reset" class="yellowBtn"><span class="yellowBtnRight">&nbsp;</span><span class="horzLine">&nbsp;</span>
                  </li>
                  <li>
                    <span class="endLine">&nbsp;</span>
                  </li>
                  <li>
                    <div class="selectChkBox">
                      <span class="fieldBold">$Lang::sb_select_string</span>
                      <input value="allpage" name="sels" type="checkbox" id="sels"><label for="page">$Lang::sb_all_onpage</label>
                    </div>
                  </li>
                </ul>
              </div>
            </div>
            <div id="jumpBarNavBottom">
$jump_bar
            </div>
            <div>
$hidden_inputs
            </div>
          </div>
        </form>
      ));
}

##########################################################
#  JumpLink
##########################################################
#
#  Provides links for the PrintNav function.

sub JumpLink {
    my ($jump_point) = @_;
    my $search_term_jump = $search_term;
    if ($search_term_jump) {
        $search_term_jump    =~ s/ /+/g;
        foreach my $i(":",",") {
            my $hex = sprintf("%%%X", ord($i));
            $search_term_jump =~ s/$i/$hex/g;
        }
    }
    # Replace spaces in location fragment with plus signs (+)
    my $jump_display_list = $display_list;
    $jump_display_list =~ s/ /+/g;
    my $jump_link = qq(href="$this_script?sk=$skin&list=$jump_display_list&sort=$sort_criteria&week=$date_range&rppg=$recs_per_page&stpt=$jump_point&submit=Search&text=$search_term_jump);
    if (@checked_records) {
        for my $i (@checked_records) {
            $jump_link .= qq(&check=$i);
        }
    }
    $jump_link .= q(");
    return $jump_link;
}

##########################################################
#  PrintNav
##########################################################
#
#  Creates the pagination/navigation buttons

sub PrintNav {
    use integer;
    my $final_total = $total_count - 1;
    my $minus_two   = $starting_pnt - (2 * $recs_per_page);
    my $minus_one   = $starting_pnt - (1 * $recs_per_page);
    my $plus_one    = $starting_pnt + (1 * $recs_per_page);
    my $plus_two    = $starting_pnt + (2 * $recs_per_page);
    my $jump_string = qq(              
              <ul class="jumpBar">);
    if ($starting_pnt > 1) {
        my $previous_link = JumpLink($minus_one);
        my $previous_tab  = qq(
                <li class="jumpBarTabLeft">
                  <a $previous_link class="jumpBarPrevious"><span class="jumpBarLeft">&nbsp;</span><span class="jumpBarArrowLeft">&nbsp;</span><span class="jumpBarButton">$Lang::nav_prev</span><span class="jumpBarEndCap">&nbsp;</span></a>
                </li>
        );
        my $link = JumpLink(1);
        $link = qq(
                <li class="jumpBarMiddle">
                  <a $link class="jumpBarLink"><span>1</span></a>
                </li>);
        $jump_string = $jump_string . $previous_tab . $link;
    } elsif ($recs_per_page < $final_total) {
        $jump_string .= qq(
                <li class="jumpBarMiddle">
                  <span class="jumpBarLabelSelected">1</span>
                </li>);
    } else {
        $jump_string .= qq(
                <li class="jumpBarMiddle">
                  <span class="jumpBarLabelSelected">1</span>
                </li>);
    }
    if ($minus_two > 1) {
        my $page_no = (($minus_two / $recs_per_page) + 1);
        my $link = JumpLink($minus_two);
        if ($minus_two > (1 + $recs_per_page)) {
            $jump_string .= qq(
                <li class="jumpBarMiddle">
                  <span class="jumpBarLabel">...</span>
                </li>
                <li class="jumpBarMiddle">
                  <a $link class="jumpBarLink"><span>$page_no</span></a>
                </li>);
        } else {
            $jump_string .= qq(
                <li class="jumpBarMiddle">
                  <a $link class="jumpBarLink"><span>$page_no</span></a>
                </li>);
        }
    }
    if ($minus_one > 1) {
        my $page_no = (($minus_one / $recs_per_page) + 1);
        my $link = JumpLink($minus_one);
        $jump_string .= qq(
                <li class="jumpBarMiddle">
                  <a $link class="jumpBarLink"><span>$page_no</span></a>
                </li>);
    }
    if ($starting_pnt > 1) {
        my $page_no = (($starting_pnt / $recs_per_page) + 1);
        $jump_string .= qq(
                <li class="jumpBarMiddle">
                  <a class="jumpBarLabelSelected"><span>$page_no</span></a>
                </li>);
    }
    if ($plus_one <= $final_total) {
        my $page_no = (($plus_one / $recs_per_page) + 1);
        my $link = JumpLink($plus_one);
        $jump_string .= qq(
                <li class="jumpBarMiddle">
                  <a $link class="jumpBarLink"><span>$page_no</span></a>
                </li>);
    }
    if ($plus_two <= $final_total) {
        my $page_no = (($plus_two / $recs_per_page) + 1);
        my $link = JumpLink($plus_two);
        $jump_string .= qq(
                <li class="jumpBarMiddle">
                  <a $link class="jumpBarLink"><span>$page_no</span></a>
                </li>);
        if (($plus_two + $recs_per_page) < $final_total) {
            my $last_link = 
              ($final_total - ($final_total % $recs_per_page) +1 ); 
            if ($last_link > $final_total ) {
                $last_link = $last_link - $recs_per_page;
            }
            my $page_no = (($last_link / $recs_per_page) + 1);
            my $link = JumpLink($last_link);
            $jump_string .= qq(
                <li class="jumpBarMiddle">
                  <span class="jumpBarLabel">...</span>
                </li>
                <li class="jumpBarMiddle">
                  <a $link class="jumpBarLink"><span>$page_no</span></a>
                </li>);
        }
    }
    if (($starting_pnt + $recs_per_page) <= $final_total) {
        my $link = JumpLink($plus_one);
        $jump_string .= qq(
                <li class="jumpBarTabRight">
                  <a $link class="jumpBarNext"><span class="jumpBarEndCap">&nbsp;</span><span class="jumpBarButton">$Lang::nav_next</span><span class="jumpBarArrowRight">&nbsp;</span><span class="jumpBarRight">&nbsp;</span></a>
                </li>);
    }

    $jump_string .= qq(
              </ul>
            );

    return "$jump_string";
}

##########################################################
#  PopulateIndex
##########################################################
#
#  Takes each record that has met the date range criteria
#  and populates an anonymous array. An index is populated
#  with these entries using each record's value of the sort
#  criteria (author|title|call number) as a key.
#

sub PopulateIndex {
    my ($sort_criteria, $bib_id, $author, $title, $edition, $imprint, $location, $location_temp, $dispcallno, $callno, $bib_format, $isbn) = @_;
#    no strict 'refs';
    # Create an anonymous array for each entry
    my $rlEntry = [$bib_id, $author, $title, $edition, $imprint, $location, $location_temp, $dispcallno, $callno, $bib_format, $isbn];
    # Add to the index
    my $sort_element;
    if ($sort_criteria eq 'title') {
        $sort_element = $title;
    } elsif ($sort_criteria eq 'author') {
        $sort_element = $author;
    } else {
        $sort_element = $callno;
    } 
    push (@{$index{$sort_element}}, $rlEntry);
#    print "Content-Type: text/html\n\n";
#    print "Printing... $sort_criteria $callno $sort_element";
#    exit(3);
}


##########################################################
#  SaveForHTML
##########################################################
#
#  The "chosen" records are packaged for HTML display and
#  returned as a list.

sub SaveForHTML {
    my ($rlEntry) = @_;
    #  0 $bib_id
    my $bib_id        = $rlEntry->[0];
    #  1 $author
    my $author        = $rlEntry->[1];
    #  2 $title
    my $title         = $rlEntry->[2];
    #  3 $edition
    my $edition       = $rlEntry->[3];
    #  4 $imprint
    my $imprint       = $rlEntry->[4];
    #  5 $location
    my $location      = $rlEntry->[5];
    #  6 $location_temp
    my $location_temp = $rlEntry->[6];
    #  7 $dispcallno
    my $dispcallno    = $rlEntry->[7];
    #  8 $callno
    my $callno        = $rlEntry->[8];
    #  9 $bib_format
    my $bib_format    = $rlEntry->[9];
    # 10 $isbn
    my $isbn          = $rlEntry->[10];
    my $thumbnail_html = '';
    if ($isbn) {
        if ($NewBooksIni::thumbnails eq "g") {
            $thumbnail_html = qq(
                    <div class="thumbNail">
                      <a href="#info" class="gbsv" title="ISBN:$isbn"><img src="one-transparent.gif" class="gbsv" alt="ISBN:$isbn" border="0"></a>
                    </div>);
        } elsif ($NewBooksIni::thumbnails eq "s") {
            $thumbnail_html = qq(
                    <div class="thumbNail">
                      <img src="http://syndetics.com/hw7.pl?isbn=$isbn/sc.gif&client=$NewBooksIni::syndetics_client_code" alt="ISBN:$isbn">
                    </div>);
        }
    }
    if ($search_term) {
        $title  = HiLiteIt($title);
        $author = HiLiteIt($author);
        $callno = HiLiteIt($callno);
#        $title  =~ s#\b($search_term)\b#<span class="highlight">$1</span>#ig;
#        $author =~ s#\b($search_term)\b#<span class="highlight">$1</span>#ig;
#        $callno =~ s#\b($search_term)\b#<span class="highlight">$1</span>#ig;
    }
    if ($row_class eq "oddRow") {
	$row_class = "evenRow";
    } else {
	$row_class = "oddRow";
    }
    @html = (@html, qq(
                <div class="$row_class">
                  <div class="resultListCheckBox">
                    <input type="checkbox" name="check" value="$display_count"));
    if (@checked_records) {
        foreach my $i (@checked_records) {
            if ($i eq $total_count) {
                @html = (@html, "checked=\"checked\"");
                last;
            }
        }
    }
#    @html = (@html, qq(> $display_count));
    @html = (@html, qq(>));

    my ($format_alt_tag, $format_image) = ProcessFormatCode($bib_format);

    @html = (@html, qq(
                  </div>
                  <div class="resultListIcon">
                    <img title="$format_alt_tag" alt="$format_alt_tag" src="ui/$skin/images/bibFormat/$format_image">
                  </div>
                  <div class="resultListCellBlock">
                    <div class="resultListTextCell">));

    $title =~ s/^(.*\S)\s?$/$1/;

    @html = (@html, qq(
                      <div class="line1Link">
                        <a href="holdingsInfo?bibId=$bib_id">$title</a>
                      </div>));

    if ( $edition ) {
        @html = (@html, qq($edition));
    }
    if ($author) {
        @html = (@html, qq( 
                      <div>$author</div>));
    }
    if ( $NewBooksIni::show_imprint =~ /^y/i ) {
        @html = (@html, qq(
                      <div>$imprint</div>));
    }
    if ($Lang::call_number_preface) {
        @html = (@html, qq(
                      <div>$Lang::call_number_preface $dispcallno</div>));
    } else {
        @html = (@html, qq(
                      <div>$dispcallno</div>));
    }
    if ($Lang::location_preface) {
         @html = (@html, qq(
                      <div>$Lang::location_preface $location</div>));
    } else {
         @html = (@html, qq(
                      <div>$location</div>));
    }
    if ( $location_temp ) {
        @html = (@html, qq(
                      <div><i>$Lang::location_temp_preface $location_temp</i></div>));
    }
    @html = (@html, qq(
                    </div>$thumbnail_html
                  </div>
                </div>));
}

##########################################################
#  SaveForPrint
##########################################################
#
#  The "chosen" records are packaged for print/save.

sub SaveForPrint {
    my ($rlEntry) = @_;
    if ( $which_records eq 'allsel' ) {
        foreach my $i (@checked_records) {
            if ( $i == $total_count ) {
                AddPrintRecord($rlEntry);
            }
        }
    } elsif ( $which_records eq 'allpage' ) {
        if ( $display_count >= $starting_pnt &&
             $display_count <= $ending_pnt ) {
            AddPrintRecord($rlEntry);
        }
    } else {
        foreach my $i (@checked_records) {
            if ( $i == $display_count &&
                 $i >= $starting_pnt  &&
                 $i <= $ending_pnt ) {
                AddPrintRecord($rlEntry);
            }
        }
    }
}


##########################################################
#  AddPrintRecord
##########################################################
#
#  The "chosen" records are packaged for print/save

sub AddPrintRecord {
    my ($rlEntry) = @_;
    #  0 $bib_id
    #  1 $author
    #  2 $title
    #  3 $edition
    #  4 $imprint
    #  5 $location
    #  6 $location_temp
    #  7 $dispcallno
    #  8 $callno
    #  9 $bib_format
    # 10 $isbn
    my $title_display = $rlEntry->[2];
    if ($rlEntry->[3]) {
        @print = (@print, qq(
$rlEntry->[2], $rlEntry->[3]));
    } else {
        @print = (@print, qq(
$rlEntry->[2]));
    }
    if ($rlEntry->[1]) {
    @print = (@print, qq(
$rlEntry->[1]));
    }
    if ($rlEntry->[4]) {
    @print = (@print, qq(
$rlEntry->[4]));
    }
    if ($rlEntry->[6]) {
    @print = (@print, qq(
$rlEntry->[5]
$Lang::location_temp_preface $rlEntry->[6]));
    } else {
    @print = (@print, qq(
$rlEntry->[5]));
    }
    @print = (@print, qq(
$rlEntry->[7]
));
}


##########################################################
#  ProcessFormatCode
##########################################################

sub ProcessFormatCode {
    my ($format_code) = @_;
    my $format_alt_tag = '';
    my $format_image   = '';
    my %format_icons = (
        'Book Icon'          => 'icon_book.gif',
        'Electronic Resource Icon' => 'icon_cfile.gif',
        'Manuscript Icon'    => 'icon_manuscript.gif',
        'Map Icon'           => 'icon_map.gif',
        'Mixed Media Icon'   => 'icon_mixed.gif',
        'Music Icon'         => 'icon_music.gif',
        'Pamphlet Icon'      => 'icon_pamphlet.gif',
        'Recording Icon'     => 'icon_recording.gif',
        'Serial Icon'        => 'icon_serial.gif',
        'Video Icon'         => 'icon_video.gif',
        'Visual Icon'        => 'icon_visual.gif'
     );
    if ($format_code eq 'am') {
        $format_alt_tag = "Book Icon";
        $format_image   = "icon_book.gif";
    } elsif (substr($format_code,0,1) eq 'c'
          || substr($format_code,0,1) eq 'd') {
        $format_alt_tag = "Music Icon";
        $format_image   = "icon_music.gif";
    } elsif (substr($format_code,0,1) eq 'e' 
          || substr($format_code,0,1) eq 'f') {
        $format_alt_tag = "Map Icon";
        $format_image   = "icon_map.gif";
    } elsif  (substr($format_code,0,1) eq 'g') {
        $format_alt_tag = "Video Icon";
        $format_image   = "icon_video.gif";
    } elsif (substr($format_code,0,1) eq 'i'
          || substr($format_code,0,1) eq 'j') {
        $format_alt_tag = "Recording Icon";
        $format_image   = "icon_recording.gif";
    } elsif (substr($format_code,0,1) eq 'k') {
        $format_alt_tag = "Visual Icon";
        $format_image   = "icon_visual.gif";
    } elsif (substr($format_code,0,1) eq 'm') {
        $format_alt_tag = "Electronic Resource Icon";
        $format_image   = "icon_cfile.gif";
    } elsif (substr($format_code,0,1) eq 'o'
          || substr($format_code,1,1) eq 'p') {
        $format_alt_tag = "Mixed Media Icon";
        $format_image   = "icon_mixed.gif";
    } elsif (substr($format_code,0,1) eq 't') {
        $format_alt_tag = "Manuscript Icon";
        $format_image   = "icon_manuscript.gif";
    } elsif (substr($format_code,1,1) eq 's'
          || substr($format_code,1,1) eq 'b') {
        $format_alt_tag = "Serial Icon";
        $format_image   = "icon_serial.gif";
    } else {
        $format_alt_tag = "Book Icon";
        $format_image   = "icon_book.gif";
    } 
    return($format_alt_tag, $format_image);
}

##########################################################
#  GetOrigDataStream
##########################################################

sub GetOrigDataStream {
    my ($remote_url) = @_;
    eval("use LWP::UserAgent");
    if ($@) {
        ErrorOutput("fatal","This script  requires the Perl LWP::UserAgent module\n");
    }

    my $ua = LWP::UserAgent->new(agent => $ENV{SCRIPT_NAME});

    my $r = HTTP::Request->new('GET',
        "$remote_url");
    if (defined $lwp_opts) {
        (@LWP::Protocol::http::EXTRA_SOCK_OPTS  ) = (@$lwp_opts);
    } 
    my $response = $ua->request($r);

    unless ($response->is_success) {
        print $response->error_as_HTML . "\n";
        print "Could not connect to server\n";
        exit(1);
    }

    my $data_out = $response->content(); # content without HTTP header

    return $data_out;
}


##########################################################
#  ReadParse
##########################################################
#
#  ReadParse reads in and parses the CGI input.
#  It reads  / QUERY_STRING ("get"  method)
#            \    STDIN     ("post" method)

sub ReadParse {
    my ($meth, $formdata, $pair, $name, $value);

    # Retrieve useful ENVIRONMENT VARIABLES
    $meth = $ENV{'REQUEST_METHOD'};

    # If method unspecified or if method is GET
    if ($meth eq  '' || $meth eq 'GET') {
        # Read in query string
        $formdata = $ENV{'QUERY_STRING'};
    }
    # If method is POST
    elsif ($meth eq 'POST') {
        read(STDIN, $formdata, $ENV{'CONTENT_LENGTH'});
    }
    else {
        die "Unknown request method: $meth\n";
    }

    # name-value pairs are separated and put into a list array
    my @pairs = split(/&/, $formdata);

    foreach $pair (@pairs) {
        # names and values are split apart
        ($name, $value) = split(/=/, $pair);
        # pluses (+'s) are translated into spaces
        $value =~ tr/+/ /;
        # hex values (%xx) are converted to alphanumeric
        $name  =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack("C", hex($1))/eg;
        $value =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack("C", hex($1))/eg;
        # The code below attempts to ferret out shell meta-characters
        # in the form input.  It replaces them with spaces.
        # looking for the presence of shell meta-characters in $name
        $name  =~ s/[{}\!\$;><&\*'\|]/ /g;
        # looking for the presence of shell meta-characters in $value
        if ($name eq "text" || $name eq "qstr") {
            $value =~ s/[{}\$><\|]/ /g;
        } else {
            $value =~ s/[{}\!\$;><&\*'\|]/ /g;
        }
        if ($name eq "check") {
            @checked_records = (@checked_records, "$value");
        } else {
            # associative array of names and values created
            $formdata{$name} = $value;
        }
    }
    # De-dup and sort the list of checked records
    if (@checked_records) {
        my %seen = ();
        my @uniq = ();
        foreach my $i (@checked_records) {
            push (@uniq, $i) unless $seen{$i}++;
        }
        @checked_records = (sort { $a <=> $b } @uniq);
    }
}


############################################################
#  MetaData
############################################################

sub MetaData {
    my $thumbnail_js = '';
    my $utf_string = decode_utf8("WebVóyage");
    my $keywords = "$utf_string $Lang::this_service";
    if ($NewBooksIni::thumbnails eq "g") {
        $thumbnail_js = q(
    <!-- Start of book cover thumbnail javascript -->
    <script type="text/javascript" src="jquery-1.2.3.min.js"></script>
    <script type="text/javascript" src="gbsv-jquery.js"></script>
    <script type="text/javascript">
        $(function(){$.GBSV.init();})
    </script>
    <!-- End of book cover thumbnail javascript -->);
    } elsif ($NewBooksIni::thumbnails eq "s") {
    } else {
    }
    my $meta_data = qq(
    <meta name="DC.Title"     content="New Books List $version">
    <meta name="DC.Creator"   content="Michael Doran">
    <meta name="DC.Type"      content="Software">
    <meta name="DC.Source"    content="http://rocky.uta.edu/doran/newbooks/">
    <meta name="DC.Publisher" content="University of Texas at Arlington Library">
    <meta name="DC.Rights"    content="Copyright 2000-2017 University of Texas at Arlington">
    <meta name="keywords"     content="$keywords">$thumbnail_js
    );
    return($meta_data);
}


############################################################
#  SearchFormHTML 
############################################################

sub SearchFormHTML {
#    my $boxsize = (@NewBooksIni::locations / 2) + 1 ;
    my $boxsize = '1' ;
    my $is_selected = '';
    if (! $display_list) {
         $display_list = "all";
    }
    if (! $date_range) {
         $date_range = "1";
    }
    if (! $sort_criteria) {
         $sort_criteria = "callno";
    }
    my $search_form = qq(
          <form id="newBooks" action="$this_script" accept-charset="UTF-8" method="get">
            <div id="searchParams">
              <div id="searchInputs" class="inputStyle">
                <label>$Lang::select_location_label</label>
                <select name="list" size="$boxsize">);
    if ($display_list ne 'all') {
        $is_selected = "";
    } else {
        $is_selected = "selected";
    }
    $search_form .= qq(
                  <option $is_selected value="all">$Lang::all_locations_text</option>);
    while (@NewBooksIni::locations) {
        my $fragment = shift(@NewBooksIni::locations);
        my $display  = shift(@NewBooksIni::locations);
        if ($display_list eq $fragment) {
            $is_selected = "selected";
        } else {
            $is_selected = "";
        }
        $search_form .= qq(
                  <option $is_selected value="$fragment">$display</option>);
    }
    $search_form .= qq(
                </select>);
    if ($Lang::last_text_order eq "after" && $Lang::swap_last_and_interval eq "yes") {
        $Lang::interval        = "$Lang::interval_plural $Lang::last_text";
        $Lang::interval_plural = "$Lang::interval_plural $Lang::last_text";
        $Lang::last_text = "";
    } elsif ($Lang::last_text_order eq "after") {
        $Lang::interval        = "$Lang::last_text $Lang::interval_plural";
        $Lang::interval_plural = "$Lang::last_text $Lang::interval_plural";
        $Lang::last_text = "";
    }

    $search_form .= qq(
                <label>$Lang::display_interval_label</label>
                <select name="week" size="1">);
    if ($date_range eq "1") {
        $is_selected = "selected";
    } else {
        $is_selected = "";
    }
    $search_form .= qq(
                  <option $is_selected value="1">$Lang::last_text $Lang::interval</option>);
    if ($date_range eq "2") {
        $is_selected = "selected";
    } else {
        $is_selected = "";
    }
    $search_form .= qq(
                  <option $is_selected value="2">$Lang::last_text 2 $Lang::interval_plural</option>);
    if ($date_range eq "3") {
        $is_selected = "selected";
    } else {
        $is_selected = "";
    }
    $search_form .= qq(
                  <option $is_selected value="3">$Lang::last_text 3 $Lang::interval_plural</option>);
    if ($date_range eq "4") {
        $is_selected = "selected";
    } else {
        $is_selected = "";
    }
    if ($search_term) {
        $search_term =~ s/"/&quot;/g;
    }
    $search_form .= qq(
                  <option $is_selected value="4">$Lang::last_text 4 $Lang::interval_plural</option>
                </select>
                <br><br>
                <label>$Lang::search_for_label</label>
                <input type="text" name="text" value="$search_term" size="30">
              </div>
            </div>
            <div title="" id="searchRecs">
              <label>$Lang::records_per_page_label</label>
              <select name="rppg" size="1">);
    if (! $recs_per_page) {
        $recs_per_page = "10";
    }
    if ($recs_per_page eq "10") {
        $is_selected = "selected"
    } else {
        $is_selected = ""
    }
    $search_form .= qq(
                <option $is_selected value="10">10 $Lang::records_per_page</option>);
    if ($recs_per_page eq "20") {
        $is_selected = "selected"
    } else {
        $is_selected = ""
    }
    $search_form .= qq(
                <option $is_selected value="20">20 $Lang::records_per_page</option>);
    if ($recs_per_page eq "25") {
        $is_selected = "selected"
    } else {
        $is_selected = ""
    }
    $search_form .= qq( 
                <option $is_selected value="25">25 $Lang::records_per_page</option>);
    if ($recs_per_page eq "50") {
        $is_selected = "selected"
    } else {
        $is_selected = ""
    }
    $search_form .= qq(
                <option $is_selected value="50">50 $Lang::records_per_page</option>
              </select>
            </div>);
    $search_form .= qq(
            <div>
              <input type="hidden" name="sort" value="$sort_criteria">
              <input type="hidden" name="stpt" value="1">
              <input type="hidden" name="sk" value="$skin">
            </div>
            <div id="searchLinks">
              <input type="submit" name="submit" id="page.search.search.button" value="$Lang::search_button">
            </div>
          </form>
    );
    return $search_form;
}


############################################################
#  GrabInc
############################################################
#
#  Returns "include" files to a scalar.
#  Usage: GrabInc ("../somefile.inc");

sub GrabInc {
    my ($inc_file) = @_;
    my $file_contents = '';
    open (INCLUDE, "$inc_file")  || warn "Can't open file.\n";
    while (<INCLUDE>) {
        $file_contents = $file_contents . $_ ;
    }
    return($file_contents);
    close (INCLUDE);
}

sub ErrorOutput {
    my ($type, $error_message) = @_;
    $error_out_count++;
    if ($ENV{'SERVER_PROTOCOL'} =~ /http/i ) {
        if ($error_out_count < 2) {
            print "Content-Type: text/html\n\n";
        }
        print "<h2>$error_message</h2>";
    } else {
        print "$error_message" . "\n";
    }
    if ($type =~ /fatal/i) {
      exit(2);
    }
}

exit(0);
