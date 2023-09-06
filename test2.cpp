#include <iostream>
using namespace std;
int i = 0;
class mc {
    public:
        mc( int i ) {
            cout << i << endl;
        }
        mc(const mc &t) {
            cout << "2" << endl;
        }
};

int main() {
    mc *t1, *t2;
    t1 = new mc(0);
    t2 = new mc(*t1);
    mc t3 = *t1, t4 = *t2;
    return 0;
}