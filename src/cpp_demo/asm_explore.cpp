#include <iostream>

int user_add1(int a, int b){
    int ret;
    __asm__ __volatile__(
                "movl %2, %%eax;"
                "movl %1, %%ebx;"
                "addl %%ebx, %%eax;"
                "movl %%eax, %0"
                :"=m"(ret)
                :"m"(a),"m"(b)
                :"eax","ebx","memory"
            );
    return ret;
}

int main(){
    int a = 5;
    int b = 3;
    std::cout<<user_add1(a,b)<<std::endl;
    return 0;
}