float test1a(float arg) 
{
    printf("blah");
    switch (blah) {
      case 1: //blah
        stuff;
        stuff;
        goto blah;
        here;
      case 0:
      case 3:
      default:
        stuff;
blah:
                    if (blah) {
            if (blah) {
                stuff;
            }
        }
    }
}

cstruct blah {
    int blah;
    int blah;
}

float test1b(const float arg) 
{
    printf("blah");
}


float test1c(const float arg) const
{
    printf("blah");
}


float test1c(const float& arg) const
{
    printf("blah");
}


//After comments
float test2a(const float& arg)
{
    printf("blah");
}

// this is commented_out (should not appear)
float test2b(const float& arg) const
{
    printf("blah");
}

/*
 * this is commented_out (should not appear)
 */
float test2c(const float& arg) const
{
    printf("blah");
}

float* test3a(const float& arg)
{
    printf("blah");
}

float* test3b(const float& arg) const
{
    printf("blah");
}

float** test3c(const float& arg) const
{
    printf("blah");
}

float * test3d(const float& arg)
{
    printf("blah");
}

float ** test3e(const float& arg)
{
    printf("blah");
}

float *** test3f(const float& arg)
{
    printf("blah");
}

float& test3g(const float& arg)
{
    return 0.0;
}

float & test3h(const float& arg)
{
    return 0.0;
}


int32_t test4a(float arg)
{
    printf("blah");
}

int32_t* test4b(const float& arg) const
{
    printf("blah");
}

int32_t* test4c(const float& arg) const
{
    if (stuff) {
        stuff;
    }
}

int32_t* test4d(const float& arg) const
{
    if should_not_be_listed(stuff) {
        stuff;
    }
}

