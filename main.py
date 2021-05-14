import sys
import model
import view

def main(argv):
    app = view.QApplication(argv)
    win = view.QMainWindow("Complevi")
    win.show()
    app.exec_()
    EXIT_SUCCESS = 0
    return EXIT_SUCCESS

if __name__ == "__main__":
    sys.exit(main(sys.argv))
