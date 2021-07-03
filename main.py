import sys
import view

def main(argv):
    app = view.QApplication(argv)
    win = view.QMainWindow("Reticulus")
    win.show()
    app.exec_()
    EXIT_SUCCESS = 0
    return EXIT_SUCCESS

if __name__ == "__main__":
    sys.exit(main(sys.argv))
