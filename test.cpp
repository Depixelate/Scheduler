#include <iostream>
#include <string>
using namespace std;
class Sample {
    string s;
    public:
    Sample(){
        cout << "s" << endl;
    }

    Sample(string arg):s(arg) {
        cout << s << endl;
    }
};

int main() {
    Sample s1;
    Sample *s2 = new Sample("s2");
    Sample *s3;
    new Sample("s4");
    return 0;
}