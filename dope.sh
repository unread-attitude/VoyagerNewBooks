#!/usr/bin/sh

#  Shell script: dope.sh - Discover Oracle-Perl Environment
#
#  version 0.9 beta
#
#  2005, Michael Doran, doran@uta.edu
#  University of Texas at Arlington Libraries
#
#  dope - information esp. from a reliable source
#  (Webster's Ninth New Collegiate Dictionary)
#  
#  Quick hack... no warranties, use at your own
#  risk, yada, yada.

dope_version="0.9 beta"

echo "DOPE $dope_version - Discover Oracle-Perl Environment\n"

#
#  Search for Solaris Perl packages
#
if [ -x /usr/bin/pkginfo ]
then
    echo `uname -a` "\n"
    echo "Searching for Solaris Perl packages..."
    pkgs="`pkginfo | grep Perl \
       | awk '{ print \"  \" $2, $3, $4, $5, $6, $7 }'`"
    if [ "$pkgs" ]
    then
        echo "$pkgs\n"
    else
        echo "  None found\n"
    fi
else
    echo "The `basename $0` utility was developed for Solaris..."
    sleep 2
    echo "  ...and you are apparently running it on another system."
    sleep 2
    echo "  Which is probably OK, but your results may vary.\n"
    sleep 5
fi

#
#  Search for 'perl' executables
#
echo "Searching for 'perl' executables..."
for perl in `find / -type f -name "perl" 2>/dev/null`
do
    if [ -x $perl ]
    then
        perl_found="yes"
        echo " " $perl
        echo "    Inode#:" `ls -i $perl | \
            awk '{print $1}'` "\tVersion:" `$perl -v | \
            grep 'This is perl' | \
            sed -e "s/.*[v ]\([\.0-9]\{2,\}\) .*/\1/"`
        modules=`$perl -e 'use ExtUtils::Installed; my $instmod = ExtUtils::Installed->new(); foreach my $module ($instmod->modules()) { my $version = $instmod->version($module) || "???"; print "      $module $version\n"; }'`
        p_modules="`echo \"$modules\" | grep -v Perl`"
        if [ "$p_modules" ]
        then
            echo "    ...has these 'after market' modules:"
            echo "$p_modules" | grep -v "Perl"
        fi
    fi
done
if [ $perl_found ]
then
    echo "  Note: Identical inode numbers indicate hard-linked files." 
else
    echo "  None found\n"
fi
    echo "  Note: There may be Perl executables under a different name.\n" 

#
#  Search for 'perl' symbolic links
#
echo "Searching for Perl symbolic links..."
for perl in `find / -type l -name "perl" 2>/dev/null`
do
if [ -x $perl ]
then
    link="yes"
    echo " " `ls $perl` `ls -l $perl | \
        sed -e "s/.*\(->.*\)/\1/"` "("`$perl -v | \
        grep 'This is perl' | \
        sed -e "s/.*[v ]\([\.0-9]\{2,\}\) .*/\1/"`")"
fi
done
if [ $link ]
then
    echo ""
else
    echo "  None found\n"
fi

#
# Search for Perl DBI module
#
echo "Searching for locations of Perl DBI module(s)..."
msg="None found\n"
for dbi in `find / -type f -name "DBI.pm" 2>/dev/null | grep -v Bundle`
do
    echo " " $dbi
    msg=""
done
echo " " $msg

#
# Search for Perl DBI module
#
echo "Searching for locations of Perl DBD::Oracle module(s)..."
msg="None found\n"
for dbi in `find / -type f -name "Oracle.pm" 2>/dev/null | grep -v Bundle`
do
    echo " " $dbi
    msg=""
done
echo " " $msg

#
# Search for Oracle versions
#
echo "Searching for Oracle versions on this system..."
for i in `find / -name product 2>/dev/null | grep oracle | grep app`
do
    if [ -d $i ]
    then
        oracle_found="yes"
        echo "  $i has these versions..."
        oracle_versions=`ls $i`
        if [ "$oracle_versions" ]
        then
            echo "    " $oracle_versions
        else
            echo "    Hmmmm.  Seems to be empty."
        fi
    fi
done
if [ ! "$oracle_found" ]
then
    echo "  None found\n"
fi
