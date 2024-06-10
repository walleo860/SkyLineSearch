
def prepend(list, str):
 
    # Using format()
    str += '{0}'
    list = [str.format(i) for i in list]
    return(list)