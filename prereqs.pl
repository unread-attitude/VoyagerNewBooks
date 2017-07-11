#!/m1/shared/bin/perl

# Utility to check for newBooks.cgi prerequisites

use strict;

EvalModules('newBooks.cgi : required Perl module(s)',
 'Encode',
 'Unicode::Normalize',
 'LWP::UserAgent',
 'Socket');

EvalModules('newBooks.pl : required Perl module(s)',
 'DBI',
 'DBD::Oracle');

EvalModules('newBooks.pl : optional Perl module(s)',
 'Net::FTP');

sub EvalModules {
    my ($message,@module_list) = @_;
    print qq($message\n);
    foreach my $module (@module_list) {
        eval("use $module");
        if ($@) {
            print qq( $module... MISSING\n);
        } else {
            print qq( $module... found\n);
        }
        sleep 1;
    }
}
