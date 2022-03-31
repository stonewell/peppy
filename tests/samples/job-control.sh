TEST=echo
#TEST=

VERBOSE=echo

PROG=`basename $0`

DELAY=1


function usage {
  echo "Usage: $PROG [command and args to repeat]"
  echo
  echo "-?      this help"
#  echo "-q      use QWERTY keyboard"
  exit 0
}

function batchrun {
  while /bin/true
  do
    $*
    sleep $DELAY
  done
}

while [ $# -gt 0 ]
do
  CHAR1=`echo "X$1" | cut -c2`
  if [ $CHAR1 = '-' ]
  then
          case $1 in
                  '-?'|'-help')
                          usage
                          ;;
                  
                  '-[1-9]')
                          #DELAY=
                          ;;
          esac
          shift
  else
          break
  fi
done
 
if [ $# -gt 0 ]
then
  batchrun $*
else
  usage
fi
