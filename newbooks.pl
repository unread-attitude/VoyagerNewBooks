#!/m1/shared/bin/perl -w

########################################################################
#
#  newbooks.pl : a New Books List program
#
#  Version: 6.1.1 for Unix
#
#  Created by Michael Doran, doran@uta.edu
#
#  University of Texas at Arlington Libraries
#  Box 19497, Arlington, TX 76019, USA
#
#  This Perl program has two distinct parts:
#   1) The first connects to the Voyager database and
#      extracts data on "new" items via an SQL query.
#   2) The second part of the script transfers the
#      flat-file database to where it can be accessed
#      by the New Books CGI program (newbooks.cgi).
#
#  More information at: http://rocky.uta.edu/doran/autolist/
#
########################################################################
#
#  Copyright 2000-2005, The University of Texas at Arlington ("UTA").
#  All rights reserved.
#
#  By using this software the USER indicates that he or she 
#  has read, understood and and will comply with the following:
#
#  UTA hereby grants USER permission to use, copy, modify, and
#  distribute this software and its documentation for any 
#  purpose and without fee, provided that:
#
#  1. the above copyright notice appears in all copies of the
#  software and its documentation, or portions thereof, and
#
#  2. a full copy of this notice is included with the software 
#  and its documentation, or portions thereof, and
#
#  3. neither the software nor its documentation, nor portions
#  thereof, is sold for profit.  Any commercial sale or license
#  of this software, copies of the software, its associated
#  documentation and/or modifications of either is strictly
#  prohibited without the prior consent of UTA.
#
#  Title to copyright to this software and its associated
#  documentation shall at all times remain with UTA.  No right
#  is granted to use in advertising, publicity or otherwise any
#  trademark, service mark, or the name of UTA.
#
#  This software and any associated documentation are provided
#  "as is," and UTA MAKES NO REPRESENTATIONS OR WARRANTIES,
#  EXPRESSED OR IMPLIED, INCLUDING THOSE OF MERCHANTABILITY OR
#  FITNESS FOR A PARTICULAR PURPOSE, OR THAT USE OF THE SOFTWARE,
#  MODIFICATIONS, OR ASSOCIATED DOCUMENTATION WILL NOT INFRINGE
#  ANY PATENTS, COPYRIGHTS, TRADEMARKS OR OTHER INTELLECTUAL
#  PROPERTY RIGHTS OF A THIRD PARTY. UTA, The University of Texas
#  System, its Regents, officers, and employees shall not be
#  liable under any circumstances for any direct, indirect, special,
#  incidental, or consequential damages with respect to any claim
#  by USER or any third party on account of or arising from the
#  use, or inability to use, this software or its associated
#  documentation, even if UTA has been advised of the possibility
#  of those damages.
#
#  Submit commercialization requests to: The University of Texas
#  at Arlington, Office of Grant and Contract Services, 701 South
#  Nedderman Drive, Box 19145, Arlington, Texas 76019-0145,
#  ATTN: Director of Technology Transfer.
#
########################################################################
#
#  "Voyager" and "WebVoyage" are trademarks of Endeavor Information
#  Systems, Inc.
#
########################################################################

#  Best practices.  :-)

use strict;

#  This program requires the DBI and DBD::Oracle modules
#  which are not a part of the default Perl distribution.
#  Endeavor installs the database modules as part of the 
#  Voyager 2000.1, or later upgrades.

use DBI;

############################################################
#  Part 1 configuration: extracting the data
############################################################
#
#  Running as a crontab entry requires that we set some
#  environment variables that would already be set if we
#  were running this from the command line while logged in.
#  To see if your values for these are the same, run the
#  "env" command while logged in as 'voyager' to your 
#  database server.

$ENV{ORACLE_SID} = "VGER";
$ENV{ORACLE_HOME} = "/oracle/app/oracle/product/9.2.0";

#  Database name
#  Substitute your database in place of xxxdb.

my $db_name = "xxxdb";

#  Name of the output flat-file of new book records
#  You probably shouldn't change this variable.

my $out_file = "newbooks.txt";

#  Voyager directory prefix
#  You probably won't need to change this variable.

my $dir_prefix = "/m1";

#  Report directory where you will temporarily store the
#  output file prior to transfering it to WebVoyage.
#  You probably won't need to change this variable.

my $report_dir = "$dir_prefix/voyager/$db_name/rpt";

#  Voyager (Oracle) read-only username and password
#  Note: The read-only username and password may be
#        different with the Unicode upgrade.
#        e.g. ro_xxxdb/ro_xxxdb

my $username = "dbread";
my $password = "dbread";


######################################
#  The SQL
#
#  The query that extracts "new" items out of the Voyager database
#  is divided into three parts that are run sequentially:
#   SQL pass 1 - physical items (may have a bib 856)
#   SQL pass 2 - electronic-only items with a mfhd 856
#   SQL pass 3 - electronic-only items with a  bib 856
#
#  The default is to run pass 1 and pass 2.  Pass 3 may pull
#  problematic items for some libraries so is optional. 
#  (For instance in our library it pulls physical items that
#  are on order but not yet received.)  Running pass 3 also
#  has the potential to produce duplicate records if your library
#  copies 856 data from the bib to the mfhd and leaves the 856 in
#  the bib record.
#
#  Details of the logic involved in how newbooks.pl defines "what
#  is a new item" (with respect to the Voyager database tables),
#  can best be determined  by examining the actual SQL code below.
#  Or, visit http://rocky.uta.edu/doran/autolist/secure/sql.htm
#  and login with username "voyager" and password "magnolia".

#  Choices are:
#	 no  (the default SQL pass 1 and pass 2) - recommended
#	 yes (the default SQL pass 1 and pass 2 *plus* pass 3)

my $pass_three = "no";


######################################
#  Intervals of weeks or months 
#
#  You have the option of retrieving either 4 weeks
#  or 4 months worth of items.  This option also
#  appears in the newbooks.ini config file.
#  Obviously, THE SELECTION YOU MAKE HERE MUST MATCH
#  the selection in newbooks.ini in order for your
#  results to make sense. 
#
#  This option was added so that smaller libraries
#  that don't add many items per week can have a
#  decent-sized new books database.

#  Choices are weeks or months.

my $intervals = "weeks";


######################################
#  Lag time 
#
#  The default lag time is one week.  This gives
#  your tech services dept that long from the time
#  the item is received (SQL option 1) or the
#  bib record is created (SQL option 2) before
#  that item is pulled for the new books list.  If
#  you notice that too many items are "In Process"
#  you can change the lag time to two weeks. 

#  Choices are 1 or 2. 

my $lag_time = "1";


############################################################
#  Part 2 configuration: transferring the output file
############################################################
#
#  There are three options for transferring the output file
#     1) Copy it to a directory - This is the obvious choice
#        if you run newbooks.pl on the same server that you
#        run the newbooks.cgi program.
#     2) Remote copy it to another server - This is the 
#        recommended method for transferring to a remote
#        server.  It requires that you create a ".rhosts"
#        file in the home directory of the voyager user on
#        the remote machine.
#     3) FTP it to another server - this requires the Perl
#        Net::FTP module (a component of the libnet collection).
#        This option requires that you include the username 
#        and password of the voyager user on the remote machine.

#  First select which option (choices are 1, 2, or 3).

my $transfer_option = "2";

#  Then edit the variables for your option choice:

######################################
#  Transfer option 1: copy
#
#  This method should be supported on
#  all Unix platforms.

#  This directory is the final destination
#  (on this server) for the output file.

my $destination_dir = "$dir_prefix/voyager/$db_name/webvoyage/cgi-bin";


######################################
#  Transfer option 2: remote copy
#
#  Remote copy uses the Perl 'system' command to run the native 
#  Unix rcp command.  IN ORDER FOR IT TO WORK you need to create
#  an .rhosts file in the home directory of the voyager user on 
#  the remote machine (i.e. the WebVoyage server).  The .rhosts 
#  file should have the following ownerships and permissions:
#	-rw-------   1 voyager  endeavor  ...   .rhosts
#
#  The /export/home/voyager/.rhosts file you just created should
#  contain an entry consisting of your database server name (the 
#  host name of the server that this script is running on) and the
#  user name (voyager) that is being allowed to do the remote copy.
#  e.g.:
#	database_server_name	voyager
#
#  Important Note: The "database_server_name" specified in the
#  rhosts file must match, exactly, the FIRST listing after the
#  IP address of that server in the /etc/inet/hosts file (or you
#  will get a "permission denied" message when trying to rcp).
#  e.g. If you use a fully qualified domain name in .rhosts:
#  	VYGRDB.UNIV.EDU  voyager
#  then the entry in the hosts file should be:
#	123.45.67.89	VYGRDB.UNIV.EDU  vygrdb  loghost
#  Conversly, if you use just the host name in .rhosts:
#	VYGRDB  voyager
#  then the entry in the hosts file should be:
#	123.45.67.89	VYGRDB  vygrdb.univ.edu  loghost
#  This is a subtle, but important point.
#
#  The remote copy method should work on all Unix platforms 
#  provided you create the .rhosts file and that you run 
#  the newbooks.pl program as the voyager user (or via the
#  voyager crontab). 
#
#  Also, on the WebVoyage server:
#  If you have turned off access to the in.rshd daemon in the
#  /etc/inet/inetd.conf file (by commenting it out) you will
#  have to make it available.  Remember to send a HUP signal
#  to the inetd process if you edit inetd.conf. 
#
#  If you are running TCP_wrappers, and you restrict in.rshd 
#  in inetd.conf, you may have to add the appropriate entry to 
#  the /etc/hosts.allow file of your WebVoyage server: 
#	in.rshd: 123.45.67.89
#  (use the IP address of your Voyager database server.)

my $remote_dir = "/m1/voyager/$db_name/webvoyage/cgi-bin";

my $webvoyage_server = "your.server.edu";

######################################
#  Transfer option 3: FTP
#
#  Since this requires you to supply the voyager username and 
#  password, I recommend that you set permissions on this script
#  to 700 (i.e. chmod 700 newbooks.pl).  The voyager user should
#  be the owner of the script.
#
#  This method should work on all Unix platforms provided 
#  you have installed the Perl libnet module containing Net::FTP.

my $ftpuser = "voyager";
my $passwd  = "xxxxxxx";

# If using option 3 (i.e. FTP), you must uncomment the following line.

# use Net::FTP;

  #       *** NOTE *** NOTE *** NOTE ***		   #
  #	The $webvoyage_server and $remote_dir variables	   #
  #	for transfer option 2 are ALSO USED for FTP        #
  #	transfers and MUST have values assigned if you     #
  #	use tranfer option 3. 				   # 


########################################################################
#
#    * * * * * * * *                          * * * * * * * *
#    * * * * * * * *    Stop editing here!    * * * * * * * *
#    * * * * * * * *                          * * * * * * * *
#
########################################################################
#
#  Most Voyager sites should not have to edit code beyond this point.
#
#  However, if you are a Perl programmer or just adventuresome, then
#  by all means have at it.  :-)
#
########################################################################


################################################################
#
#  Part 1: extracting the data
#
################################################################

#  This gets the ball rolling for part 1.

&DoQuery;

##########################################################
#  DoQuery
##########################################################
#

sub DoQuery {
    # Connect to Oracle database
    my $dbh = DBI->connect('dbi:Oracle:', $username, $password)
	|| die "Could not connect: $DBI::errstr";

    # Prepare the first SQL statement
    my $sth = $dbh->prepare(&ConstructSQL("1")) 
	|| die $dbh->errstr;

    # Run the SQL query
    $sth->execute
	|| die $dbh->errstr;

    # Output the results to a file
    open (OUTFILE, ">$report_dir/$out_file")
	|| die "Cannot create/open output file: $!";

    while( my (@entry) = $sth->fetchrow_array() ) {
	if ($entry[0]) { 
	    print OUTFILE "$entry[0]\t"; 
	} else { 
	    print OUTFILE "\t"; 
	}
	if ($entry[1]) { 
	    my $author = $entry[1];
	    print OUTFILE "$author\t"; 
	} else { 
	    print OUTFILE "\t"; 
	}
	if ($entry[2]) {
	    my $title = $entry[2];
	    print OUTFILE "$title\t"; 
	} else {
	    print OUTFILE "\t";
	}
	if ($entry[3]) { 
	    my $edition = $entry[3];
	    print OUTFILE "$edition\t"; 
	} else { 
	    print OUTFILE "\t"; 
	}
	if ($entry[4]) { 
	    my $imprint = $entry[4];
	    print OUTFILE "$imprint\t"; 
	} else { 
	    print OUTFILE "\t"; 
	}
	if ($entry[5]) { 
	    my $location_display_name_permanent = $entry[5];
	    print OUTFILE "$location_display_name_permanent\t"; 
	} else { 
	    print OUTFILE "\t"; 
	} if ($entry[6]) { 
	    my $location_display_name_temporary = $entry[6];
	    print OUTFILE "$location_display_name_temporary\t"; 
	} else { 
	    print OUTFILE "\t"; 
	}
	if ($entry[7]) { 
	    my $display_call_no = $entry[7];
	    print OUTFILE "$display_call_no\t"; 
	} else { 
	    # Note: In Process entries deliberately have
	    # a leading space for sorting purposes.
	    print OUTFILE " In Process\t"; 
	}
	if ($entry[8]) { 
	    my $normalized_call_no = $entry[8];
	    print OUTFILE "$normalized_call_no\t"; 
	} else { 
	    print OUTFILE " In Process\t"; 
	}
	if ($entry[9]) { 
	    print OUTFILE "$entry[9]\t"; 
	} else { 
	    print OUTFILE "\t"; 
	}
	if ($entry[10]) { 
	    print OUTFILE "$entry[10]\t"; 
	} else { 
	    print OUTFILE "\t"; 
	}
	if ($entry[11]) { 
	    print OUTFILE "$entry[11]\n"; 
	} else { 
	    print OUTFILE "$entry[12]\n"; 
	}
    }

    # Prepare the second SQL statement
    $sth = $dbh->prepare(&ConstructSQL("2")) 
	|| die $dbh->errstr;

    # Run the SQL query
    $sth->execute
	|| die $dbh->errstr;


    # Output the results to a file
    open (OUTFILE, ">>$report_dir/$out_file")
	|| die "Cannot create/open output file: $!";

    while( my (@entry) = $sth->fetchrow_array() ) {
	if ($entry[0]) { 
	    print OUTFILE "$entry[0]\t"; 
	} else { 
	    print OUTFILE "\t"; 
	}
	if ($entry[1]) { 
	    my $author = $entry[1];
	    print OUTFILE "$author\t"; 
	} else { 
	    print OUTFILE "\t"; 
	}
	if ($entry[2]) {
	    my $title = $entry[2];
	    print OUTFILE "$title\t"; 
	} else {
	    print OUTFILE "\t";
	}
	if ($entry[3]) { 
	    my $edition = $entry[3];
	    print OUTFILE "$edition\t"; 
	} else { 
	    print OUTFILE "\t"; 
	}
	if ($entry[4]) { 
	    my $imprint = $entry[4];
	    print OUTFILE "$imprint\t"; 
	} else { 
	    print OUTFILE "\t"; 
	}
	if ($entry[5]) { 
	    my $location_display_name_permanent = $entry[5];
	    print OUTFILE "$location_display_name_permanent\t"; 
	} else { 
	    print OUTFILE "\t"; 
	}
	print OUTFILE "\t"; 
	if ($entry[6]) { 
	    my $display_call_no = $entry[6];
	    print OUTFILE "$display_call_no\t"; 
	} else { 
	    # Note: In Process entries deliberately have
	    # a leading space for sorting purposes.
	    print OUTFILE " In Process\t"; 
	}
	if ($entry[7]) { 
	    my $normalized_call_no = $entry[7];
	    print OUTFILE "$normalized_call_no\t"; 
	} else { 
	    print OUTFILE " In Process\t"; 
	}
	if ($entry[8]) { 
	    print OUTFILE "$entry[8]\t"; 
	} else { 
	    print OUTFILE "\t"; 
	}
	if ($entry[9]) { 
	    chomp (my $link_text = $entry[9]);
	    print OUTFILE "$link_text\t"; 
	} else { 
	    print OUTFILE "\t"; 
	}
	if ($entry[10]) { 
	    print OUTFILE "$entry[10]\n"; 
	} else { 
	    print OUTFILE "\n"; 
	}
    }

  if ($pass_three eq "yes") {

    # Prepare the third SQL statement
    $sth = $dbh->prepare(&ConstructSQL("3")) 
	|| die $dbh->errstr;

    # Run the SQL query
    $sth->execute
	|| die $dbh->errstr;


    # Output the results to a file
    open (OUTFILE, ">>$report_dir/$out_file")
	|| die "Cannot create/open output file: $!";

    while( my (@entry) = $sth->fetchrow_array() ) {
	if ($entry[0]) { 
	    print OUTFILE "$entry[0]\t"; 
	} else { 
	    print OUTFILE "\t"; 
	}
	if ($entry[1]) { 
	    my $author = $entry[1];
	    print OUTFILE "$author\t"; 
	} else { 
	    print OUTFILE "\t"; 
	}
	if ($entry[2]) {
	    my $title = $entry[2];
	    print OUTFILE "$title\t"; 
	} else {
	    print OUTFILE "\t";
	}
	if ($entry[3]) { 
	    my $edition = $entry[3];
	    print OUTFILE "$edition\t"; 
	} else { 
	    print OUTFILE "\t"; 
	}
	if ($entry[4]) { 
	    my $imprint = $entry[4];
	    print OUTFILE "$imprint\t"; 
	} else { 
	    print OUTFILE "\t"; 
	}
	if ($entry[5]) { 
	    my $location_display_name_permanent = $entry[5];
	    print OUTFILE "$location_display_name_permanent\t"; 
	} else { 
	    print OUTFILE "\t"; 
	}
	print OUTFILE "\t"; 
	if ($entry[6]) { 
	    my $display_call_no = $entry[6];
	    print OUTFILE "$display_call_no\t"; 
	} else { 
	    # Note: In Process entries deliberately have
	    # a leading space for sorting purposes.
	    print OUTFILE " In Process\t"; 
	}
	if ($entry[7]) { 
	    my $normalized_call_no = $entry[7];
	    print OUTFILE "$normalized_call_no\t"; 
	} else { 
	    print OUTFILE " In Process\t"; 
	}
	if ($entry[8]) { 
	    print OUTFILE "$entry[8]\t"; 
	} else { 
	    print OUTFILE "\t"; 
	}
	if ($entry[9]) { 
	    chomp (my $link_text = $entry[9]);
	    print OUTFILE "$link_text\t"; 
	} else { 
	    print OUTFILE "\t"; 
	}
	if ($entry[10]) { 
	    print OUTFILE "$entry[10]\n"; 
	} else { 
	    print OUTFILE "\n"; 
	}
    }

  }

    $sth->finish;

    $dbh->disconnect;

    close (OUTFILE);

}



##########################################################
#  SetInterval
##########################################################

sub SetInterval {
    my ($one_or_two) = @_;
    my ($date_condition_one,$date_condition_two);
    if ($intervals eq "weeks") {
	if ($lag_time eq "1") {
	    $date_condition_one = " / 7) - 1)";
	    $date_condition_two = "(sysdate - 35) and (sysdate - 7)";
        } elsif ($lag_time eq "2") {
	    $date_condition_one = " / 7) - 2)";
	    $date_condition_two = "(sysdate - 42) and (sysdate - 14)";
	} else {
	    print "Error: no lag time option selected.\n";
	    exit (22);
	}
    } elsif ($intervals eq "months") {
	if ($lag_time eq "1") {
	    $date_condition_one = "-  7) / 30) ";
	    $date_condition_two = "(sysdate - 127) and (sysdate - 7)";
        } elsif ($lag_time eq "2") {
	    $date_condition_one = "- 14) / 30) ";
	    $date_condition_two = "(sysdate - 134) and (sysdate - 14)";
	} else {
	    print "Error: no lag time option selected.\n";
	    exit (22);
	}
    } else {
	print "Error: no interval option selected.\n";
	exit (22);
    }
    if ($one_or_two eq "one") {
	return($date_condition_one);
    } elsif ($one_or_two eq "two") {
	return($date_condition_two);
    }
}


##########################################################
#  ConstructSQL
##########################################################
#
#  This routine returns an SQL query according to which
#  option was selected in the configuration section.

sub ConstructSQL {
    my ($sql_pass) = @_;
    #  The SQL option "choice" is an artifact of previous
    #  versions.  This SQL query's embedded logic as to
    #  "what constitutes a new item" should be adequate
    #  for all sites.  If it isn't, you may create your
    #  own; however, it must output the same fields in
    #  order for the newbooks.cgi to utilize it.  -mdd
    my $date_condition_one = &SetInterval("one");
    my $date_condition_two = &SetInterval("two");
    if ($sql_pass eq "1") {
	return ("
	select distinct
	  $db_name.bib_text.bib_id,
	  $db_name.bib_text.author,
	  $db_name.bib_text.title,
	  $db_name.bib_text.edition,
	  $db_name.bib_text.imprint,
	  $db_name.permanent.location_display_name,
	  $db_name.temporary.location_display_name,
	  $db_name.mfhd_master.display_call_no,
	  $db_name.mfhd_master.normalized_call_no,
	  $db_name.elink_index.link,
	  $db_name.elink_index.link_text,
	  (ceil (((sysdate - $db_name.mfhd_master.update_date) $date_condition_one),
	  (ceil (((sysdate - $db_name.mfhd_master.create_date) $date_condition_one)
	from
	  $db_name.bib_master,
	  $db_name.bib_text,
	  $db_name.bib_mfhd,
	  $db_name.mfhd_item,
	  $db_name.mfhd_master,
	  $db_name.item,
	  $db_name.location permanent,
	  $db_name.location temporary,
	  $db_name.elink_index
	where
	  $db_name.bib_master.bib_id=$db_name.bib_text.bib_id and
	  $db_name.bib_text.bib_id=$db_name.bib_mfhd.bib_id and
	  $db_name.bib_mfhd.mfhd_id=$db_name.mfhd_master.mfhd_id and
	  $db_name.mfhd_master.mfhd_id=$db_name.mfhd_item.mfhd_id and
	  $db_name.mfhd_item.item_id=$db_name.item.item_id and
	  $db_name.item.perm_location=$db_name.permanent.location_id and
	  $db_name.item.temp_location=$db_name.temporary.location_id(+) and
	  $db_name.bib_master.bib_id=$db_name.elink_index.record_id(+) and
	  $db_name.mfhd_master.suppress_in_opac not in ('Y') and
	  $db_name.bib_master.suppress_in_opac not in ('Y') and
	  ($db_name.elink_index.record_type in ('B') or
	   $db_name.elink_index.record_type is null) and
	  $db_name.item.on_reserve not in ('Y') and
	  substr($db_name.bib_text.bib_format,-1,1) in ('a','c','m') and
	  $db_name.item.create_date between $date_condition_two and 
	  ($db_name.mfhd_master.create_date between $date_condition_two or
	   $db_name.mfhd_master.update_date between $date_condition_two)
	");
    } elsif ($sql_pass eq "2") {
	return ("
	select distinct
	  $db_name.bib_text.bib_id,
	  $db_name.bib_text.author,
	  $db_name.bib_text.title,
	  $db_name.bib_text.edition,
	  $db_name.bib_text.imprint,
	  $db_name.location.location_display_name,
	  $db_name.mfhd_master.display_call_no,
	  $db_name.mfhd_master.normalized_call_no,
	  $db_name.elink_index.link,
	  $db_name.elink_index.link_text,
	  (ceil (((sysdate - $db_name.mfhd_master.create_date) $date_condition_one)
	from
	  $db_name.bib_master,
	  $db_name.bib_text,
	  $db_name.bib_mfhd,
	  $db_name.mfhd_master,
	  $db_name.mfhd_item,
	  $db_name.location,
	  $db_name.elink_index
	where
	  $db_name.bib_master.bib_id=$db_name.bib_text.bib_id and
	  $db_name.bib_text.bib_id=$db_name.bib_mfhd.bib_id and
	  $db_name.bib_mfhd.mfhd_id=$db_name.mfhd_master.mfhd_id and
	  $db_name.mfhd_master.location_id=$db_name.location.location_id and
	  $db_name.mfhd_master.mfhd_id=$db_name.elink_index.record_id and
	  $db_name.elink_index.record_type in ('M') and
	  $db_name.mfhd_master.mfhd_id=$db_name.mfhd_item.mfhd_id(+) and
	  $db_name.mfhd_item.item_id is null and
	  $db_name.mfhd_master.suppress_in_opac not in ('Y') and
	  $db_name.bib_master.suppress_in_opac not in ('Y') and
	  $db_name.mfhd_master.create_date between $date_condition_two and
	  $db_name.elink_index.link is not null
	");
    } elsif ($sql_pass eq "3") {
	return ("
	select distinct
	  $db_name.bib_text.bib_id,
	  $db_name.bib_text.author,
	  $db_name.bib_text.title,
	  $db_name.bib_text.edition,
	  $db_name.bib_text.imprint,
	  $db_name.location.location_display_name,
	  $db_name.mfhd_master.display_call_no,
	  $db_name.mfhd_master.normalized_call_no,
	  $db_name.elink_index.link,
	  $db_name.elink_index.link_text,
	  (ceil (((sysdate - $db_name.mfhd_master.create_date) $date_condition_one)
	from
	  $db_name.bib_master,
	  $db_name.bib_text,
	  $db_name.bib_mfhd,
	  $db_name.mfhd_master,
	  $db_name.mfhd_item,
	  $db_name.location,
	  $db_name.elink_index
	where
	  $db_name.bib_master.bib_id=$db_name.bib_text.bib_id and
	  $db_name.bib_text.bib_id=$db_name.bib_mfhd.bib_id and
	  $db_name.bib_mfhd.mfhd_id=$db_name.mfhd_master.mfhd_id and
	  $db_name.mfhd_master.location_id=$db_name.location.location_id and
	  $db_name.bib_master.bib_id=$db_name.elink_index.record_id and
	  $db_name.elink_index.record_type in ('B') and
	  $db_name.mfhd_master.mfhd_id=$db_name.mfhd_item.mfhd_id(+) and
	  $db_name.mfhd_item.item_id is null and
	  $db_name.mfhd_master.suppress_in_opac not in ('Y') and
	  $db_name.bib_master.suppress_in_opac not in ('Y') and
	  $db_name.mfhd_master.create_date between $date_condition_two and
	  $db_name.elink_index.link is not null
	");
    } else {
	print "Error: no SQL option selected.\n";
	exit (22);
    }
}


################################################################
#
#  Part 2: transferring the output file
#
################################################################

if      ($transfer_option eq "1" ) {
    &CopyFile;
} elsif ($transfer_option eq "2" ) {
    &RemoteCopyFile;
} elsif ($transfer_option eq "3" ) {
    &SendFTP;
} else {
    print "Aborted file transmission: Incorrect transfer option chosen.\n";
}


##########################################################
#  CopyFile
##########################################################
#
#  This routine copies the output file to the directory
#  on this server where you keep newbooks.cgi.

sub CopyFile {
    use File::Copy;
#	or die "Aborted file transmission: no File::Copy";
    copy("$report_dir/$out_file","$destination_dir/$out_file")
	or die "Aborted file transmission: Can't copy file.";
}


##########################################################
#  RemoteCopyFile
##########################################################
#
#  This routine does a remote copy of the output file to
#  the directory on the server where newbooks.cgi is.

sub RemoteCopyFile {
    system("/usr/bin/rcp $report_dir/$out_file $webvoyage_server:$remote_dir/$out_file");
}


##########################################################
#  SendFTP
##########################################################
#
#  This routine sends the output file to another serve
#  via FTP.  It REQUIRES that you have the Perl libnet
#  module installed so that you can use Net::FTP.

sub SendFTP {
    # Change to directory of output file
    chdir($report_dir)
	or die "FTP: Cannot cd to $report_dir.";

    # Start FTP: connect, and login
    my $ftp = Net::FTP->new($webvoyage_server)
	or die "FTP: Couldn't connect: $@.";
    $ftp->login($ftpuser, $passwd)
	or die "FTP: Couldn't login.";

    # Change to desired webserver directory
    $ftp->cwd($remote_dir)
	or die "FTP: Couldn't change directory.";

    # Send file
    $ftp->put($out_file)
	or die "FTP: Couldn't send $out_file.";

    # Exit from the ftp session
    $ftp->quit()
	or die "FTP: Couldn't quit.";
}


############################################################
# Exit from script

exit(0);
